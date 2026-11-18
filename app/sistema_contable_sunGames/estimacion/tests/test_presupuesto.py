import inspect
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.test import TestCase

from bitacora.models import RegistroBitacora
from estimacion import calculos, composition, models, repositories, services
from estimacion.composition import (
    crear_estimacion_service,
    crear_presupuesto_service,
)
from estimacion.exceptions import (
    SalarioNoEncontradoError,
    SinRondaAprobadaError,
    VersionInmutableError,
)
from estimacion.models import (
    Rol as RolEstimacion,
    SalarioReferencia,
    VersionPresupuesto,
)
from usuarios.models import Usuario
from usuarios.roles import Rol

FECHA = date(2026, 6, 1)
APP_DIR = Path(__file__).resolve().parent.parent


class PresupuestoTests(TestCase):
    def setUp(self):
        self.estimaciones = crear_estimacion_service()
        self.presupuestos = crear_presupuesto_service()
        self.admin = Usuario.objects.create(
            username="admin", nombre_completo="Admin",
            rol=Rol.ADMINISTRADOR,
        )
        self.rol = RolEstimacion.objects.create(
            nombre="Programador", nivel=3
        )
        SalarioReferencia.objects.create(
            rol=self.rol, salario_bruto=Decimal("1200"),
            vigente_desde=date(2026, 1, 1),
        )
        self.experto = self.estimaciones.crear_experto(
            self.admin, "Experto Uno"
        )
        self.juego = self.estimaciones.crear_juego(
            self.admin, "Proyecto A"
        )
        self.fase = self.juego.fases.get(nombre="Programación")

    def estimacion(self, o, m, p, ronda=1):
        return self.estimaciones.registrar_estimacion(
            self.admin, juego_id=self.juego.pk, fase_id=self.fase.pk,
            rol_id=self.rol.pk, experto_id=self.experto.pk, ronda=ronda,
            optimista=Decimal(str(o)), moda=Decimal(str(m)),
            pesimista=Decimal(str(p)),
        )

    def ronda_aprobada(self):
        self.estimacion(400, 500, 800)
        return self.estimaciones.cerrar_ronda(
            self.admin, self.juego.pk, 1, fecha=FECHA
        )

    def test_generar_version_valores_exactos(self):
        self.ronda_aprobada()
        version = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA
        )
        self.assertEqual(version.numero, 1)
        self.assertEqual(version.estado, VersionPresupuesto.Estado.BORRADOR)
        self.assertEqual(version.lineas.count(), 1)
        linea = version.lineas.get()
        self.assertAlmostEqual(float(linea.horas_E), 533.3333, delta=0.0001)
        self.assertAlmostEqual(float(linea.sigma), 66.6667, delta=0.0001)
        self.assertAlmostEqual(float(linea.tarifa), 9.2258, delta=0.0001)
        self.assertAlmostEqual(
            float(linea.costo_mano_obra), 4920.45, delta=0.05
        )
        snapshot = version.snapshot_parametros
        parametros = snapshot["parametros"]
        self.assertEqual(
            Decimal(parametros["horas_semana"]), Decimal("44")
        )
        self.assertEqual(
            Decimal(parametros["semanas_año"]), Decimal("52")
        )
        self.assertEqual(
            Decimal(parametros["tasa_cargas_patronales"]), Decimal("0.246")
        )
        self.assertEqual(
            Decimal(parametros["eficiencia"]), Decimal("0.85")
        )
        self.assertIn(str(self.rol.pk), snapshot["salarios"])

    def test_sin_ronda_aprobada_no_genera(self):
        with self.assertRaises(SinRondaAprobadaError):
            self.presupuestos.generar_version(
                self.admin, self.juego.pk, fecha=FECHA
            )

    def test_rol_sin_salario_no_genera_y_alerta(self):
        otro_rol = RolEstimacion.objects.create(
            nombre="Artista", nivel=2
        )
        experto2 = self.estimaciones.crear_experto(
            self.admin, "Experto Dos"
        )
        self.estimaciones.registrar_estimacion(
            self.admin, juego_id=self.juego.pk, fase_id=self.fase.pk,
            rol_id=otro_rol.pk, experto_id=experto2.pk, ronda=1,
            optimista=Decimal("10"), moda=Decimal("20"),
            pesimista=Decimal("30"),
        )
        self.estimacion(400, 500, 800)
        self.estimaciones.cerrar_ronda(
            self.admin, self.juego.pk, 1, fecha=FECHA
        )
        with self.assertRaises(SalarioNoEncontradoError):
            self.presupuestos.generar_version(
                self.admin, self.juego.pk, fecha=FECHA
            )
        self.assertEqual(VersionPresupuesto.objects.count(), 0)
        alerta = RegistroBitacora.objects.get(
            accion="GENERACION_PRESUPUESTO",
            resultado="RECHAZADO",
        )
        self.assertIn("salario", alerta.detalle)

    def test_version_aprobada_es_inmutable(self):
        self.ronda_aprobada()
        version = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA
        )
        self.presupuestos.agregar_costo_directo(
            self.admin, version.pk, "Licencias", Decimal("100")
        )
        self.presupuestos.aprobar(self.admin, version.pk)
        version.refresh_from_db()
        self.assertEqual(version.estado, VersionPresupuesto.Estado.APROBADO)
        with self.assertRaises(VersionInmutableError):
            self.presupuestos.agregar_costo_directo(
                self.admin, version.pk, "Otro", Decimal("50")
            )
        with self.assertRaises(VersionInmutableError):
            self.presupuestos.aprobar(self.admin, version.pk)
        version.estado = VersionPresupuesto.Estado.BORRADOR
        with self.assertRaises(VersionInmutableError):
            version.save()

    def test_correccion_crea_version_nueva(self):
        self.ronda_aprobada()
        v1 = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA
        )
        self.presupuestos.aprobar(self.admin, v1.pk)
        v2 = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA
        )
        self.assertEqual(v2.numero, 2)
        self.assertEqual(v2.estado, VersionPresupuesto.Estado.BORRADOR)
        self.assertEqual(VersionPresupuesto.objects.count(), 2)

    def test_total_suma_todos_los_conceptos(self):
        self.ronda_aprobada()
        version = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA,
            costos_directos=(("Motores", Decimal("500")),),
            costos_indirectos=(("Administración", Decimal("300")),),
        )
        total = self.presupuestos.total(version)
        linea = version.lineas.get()
        esperado = (
            linea.costo_mano_obra + Decimal("500") + Decimal("300")
        )
        self.assertEqual(total, esperado)

    def test_marcar_vigente_desplaza_anterior(self):
        self.ronda_aprobada()
        v1 = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA
        )
        self.presupuestos.aprobar(self.admin, v1.pk)
        self.presupuestos.marcar_vigente(self.admin, self.juego.pk, v1.pk)
        v1.refresh_from_db()
        self.assertEqual(v1.estado, VersionPresupuesto.Estado.VIGENTE)
        v2 = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA
        )
        self.presupuestos.aprobar(self.admin, v2.pk)
        self.presupuestos.marcar_vigente(self.admin, self.juego.pk, v2.pk)
        v1.refresh_from_db()
        v2.refresh_from_db()
        self.assertEqual(v1.estado, VersionPresupuesto.Estado.APROBADO)
        self.assertEqual(v2.estado, VersionPresupuesto.Estado.VIGENTE)

    def test_costos_fabricacion_se_copian_a_la_version(self):
        self.estimaciones.agregar_costo_fabricacion(
            self.admin, self.juego.pk, "DIRECTO",
            "Máquinas de desarrollo", Decimal("800"),
        )
        self.estimaciones.agregar_costo_fabricacion(
            self.admin, self.juego.pk, "INDIRECTO",
            "Mantenimiento de equipo", Decimal("200"),
        )
        self.ronda_aprobada()
        version = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA
        )
        self.assertEqual(version.costos_directos.count(), 1)
        self.assertEqual(
            version.costos_directos.get().concepto,
            "Máquinas de desarrollo",
        )
        self.assertEqual(version.costos_indirectos.count(), 1)
        self.assertEqual(
            version.costos_indirectos.get().departamento,
            "Mantenimiento de equipo",
        )
        linea = version.lineas.get()
        self.assertEqual(
            self.presupuestos.total(version),
            linea.costo_mano_obra + Decimal("800") + Decimal("200"),
        )

    def test_version_rechazada_es_inmutable(self):
        self.ronda_aprobada()
        version = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA
        )
        self.presupuestos.rechazar(self.admin, version.pk)
        version.refresh_from_db()
        self.assertEqual(
            version.estado, VersionPresupuesto.Estado.RECHAZADO
        )
        with self.assertRaises(VersionInmutableError):
            self.presupuestos.agregar_costo_directo(
                self.admin, version.pk, "Otro", Decimal("50")
            )
        with self.assertRaises(VersionInmutableError):
            self.presupuestos.aprobar(self.admin, version.pk)
        v2 = self.presupuestos.generar_version(
            self.admin, self.juego.pk, fecha=FECHA
        )
        self.assertEqual(v2.numero, 2)

    def test_modulo_no_consulta_el_libro_mayor(self):
        for modulo in (models, calculos, repositories, services,
                       composition):
            fuente = inspect.getsource(modulo)
            self.assertNotIn("libro_mayor", fuente)
            self.assertNotIn("Movimiento", fuente)
        for archivo in APP_DIR.glob("*.py"):
            self.assertNotIn(
                "libro_mayor", archivo.read_text(encoding="utf-8")
            )
