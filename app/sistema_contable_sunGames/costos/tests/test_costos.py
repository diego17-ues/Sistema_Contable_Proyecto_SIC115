"""Pruebas del subsistema de costos (Etapa 1 · Fase 1).

Cubren los valores exactos exigidos por AGENTS2.md: registro de mano de
obra directa, costos directos e indirectos con su asiento en el Libro
Mayor, anulación con contra-asiento, idempotencia, cuadre, origen,
período cerrado y ausencia de los conceptos eliminados.
"""

import re
import uuid
from contextlib import nullcontext
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from django.db import transaction
from django.db.models import Sum
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from catalogo.models import Cuenta
from costos import calculos
from costos.exceptions import (
    AsientoDescuadradoError,
    ConfiguracionNoEncontradaError,
    CuentaNoValidaError,
    DatosInsuficientesError,
    OrdenDuplicadaError,
    PeriodoNoAbiertoError,
    RegistroYaAnuladoError,
)
from costos.models import (
    AsientoCosto,
    ConfiguracionCuentaCosto,
    Elemento,
    Proceso,
    RegistroCosto,
)
from costos.repositories import CostosRepository
from costos.services import (
    CatalogoCostosService,
    OrdenService,
    RegistroCostoService,
)
from libro_mayor.models import EstadoPeriodo, Movimiento, PeriodoContable
from libro_mayor.repositories import TransaccionRepository
from usuarios.models import Usuario
from usuarios.roles import Rol

D = Decimal
FECHA = date(2026, 6, 15)
APP = Path(__file__).resolve().parents[1]


def clave():
    return uuid.uuid4().hex


class CalculosPurosTests(SimpleTestCase):
    def test_importe_mano_obra(self):
        self.assertEqual(calculos.importe_mano_obra("40", "20.00"),
                         D("800.00"))
        self.assertEqual(calculos.importe_mano_obra("1.5", "33.3333"),
                         D("50.00"))

    def test_lineas_cuadran_y_contrarias(self):
        lineas = calculos.lineas_registro("debe", "haber", D("83.33"))
        self.assertEqual(lineas,
                         [("debe", D("83.33")), ("haber", D("-83.33"))])
        self.assertTrue(calculos.cuadra(lineas))
        self.assertEqual(calculos.lineas_contrarias(lineas),
                         [("debe", D("-83.33")), ("haber", D("83.33"))])
        self.assertFalse(calculos.cuadra([("debe", D("1"))]))


# ------------------------------------------------------------ unitarias

class _RepoMemoria:
    """Repositorio en memoria para probar el servicio sin base de datos."""

    def __init__(self, config):
        self.registros, self.asientos = {}, []
        self.orden = SimpleNamespace(pk=1, abierta=True)
        self.config = config
        self.proceso = SimpleNamespace(pk=7, nombre="Programación",
                                       activo=True)

    def obtener_orden(self, orden_id):
        return self.orden if orden_id == 1 else None

    def obtener_proceso(self, proceso_id):
        return self.proceso if proceso_id == 7 else None

    def configuracion(self, elemento):
        return self.config

    def registro_por_clave(self, clave):
        return self.registros.get(clave)

    def crear_registro(self, **datos):
        registro = SimpleNamespace(
            pk=len(self.registros) + 1, orden_id=datos["orden"].pk,
            get_elemento_display=lambda: "Mano de obra directa", **datos,
        )
        self.registros[datos["clave_idempotencia"]] = registro
        return registro

    def crear_asiento(self, **datos):
        self.asientos.append(datos)
        return datos


class _MayorMemoria:
    def __init__(self, cerrado=False):
        self.cerrado = cerrado
        self.movimientos = []

    def periodo_de(self, fecha):
        return SimpleNamespace(cerrado=self.cerrado)

    def tiene_subcuentas(self, cuenta):
        return False

    def crear_transaccion(self, *, usuario):
        return SimpleNamespace(pk=99)

    def crear_movimiento(self, **datos):
        self.movimientos.append(datos)


class RegistroServiceUnitTests(SimpleTestCase):
    def setUp(self):
        self.debe = SimpleNamespace(pk=1, codigo="D", activa=True)
        self.haber = SimpleNamespace(pk=2, codigo="H", activa=True)
        config = SimpleNamespace(
            cuenta_costo=self.debe, contrapartida_defecto_id=2,
            contrapartidas=SimpleNamespace(all=lambda: [self.haber]),
        )
        self.repo = _RepoMemoria(config)
        self.mayor = _MayorMemoria()
        self.actor = SimpleNamespace(activo=True, rol=Rol.CONTADOR_GENERAL)
        self.servicio = RegistroCostoService(self.repo, self.mayor, None,
                                             nullcontext)

    def _mano_obra(self, clave_="k1"):
        return self.servicio.registrar_mano_obra(
            self.actor, orden_id=1, fecha=FECHA, proceso_id=7, horas="40",
            costo_hora="20.00", contrapartida_id=None, clave=clave_,
        )

    def test_asiento_cuadrado_con_auxiliar_y_clave(self):
        registro = self._mano_obra()
        self.assertEqual(registro.importe, D("800.00"))
        importes = [m["importe"] for m in self.mayor.movimientos]
        self.assertEqual(importes, [D("800.00"), D("-800.00")])
        self.assertTrue(all("OT-1" in m["referencia"]
                            for m in self.mayor.movimientos))
        self.assertEqual(self.repo.asientos[0]["clave_idempotencia"], "k1")

    def test_misma_clave_no_duplica(self):
        primero = self._mano_obra()
        segundo = self._mano_obra()
        self.assertIs(primero, segundo)
        self.assertEqual(len(self.mayor.movimientos), 2)

    def test_periodo_cerrado_rechaza(self):
        self.mayor.cerrado = True
        with self.assertRaises(PeriodoNoAbiertoError):
            self._mano_obra()
        self.assertEqual(self.mayor.movimientos, [])

    def test_sin_configuracion_bloquea(self):
        self.repo.config = None
        with self.assertRaises(ConfiguracionNoEncontradaError):
            self._mano_obra()

    def test_asiento_descuadrado_no_se_registra(self):
        registro = SimpleNamespace(pk=1, orden_id=1)
        with self.assertRaises(AsientoDescuadradoError):
            self.servicio._asentar(
                self.actor, registro, [(self.debe, D("1"))], fecha=FECHA,
                tipo="REGISTRO", tipo_movimiento="DIARIO", concepto="x",
                clave="k",
            )
        self.assertEqual(self.mayor.movimientos, [])

    def test_horas_en_cero_rechaza(self):
        with self.assertRaises(DatosInsuficientesError):
            self.servicio.registrar_mano_obra(
                self.actor, orden_id=1, fecha=FECHA, proceso_id=7,
                horas="0", costo_hora="20", contrapartida_id=None,
                clave="k2",
            )


# ---------------------------------------------------------- integración

class BaseCostos(TestCase):
    def setUp(self):
        self.actor = Usuario.objects.create(
            username="contador", nombre_completo="Contador",
            rol=Rol.CONTADOR_GENERAL, activo=True,
        )
        self.repo = CostosRepository()
        self.ordenes = OrdenService(self.repo, None, transaction.atomic)
        self.servicio = RegistroCostoService(
            self.repo, TransaccionRepository(), None, transaction.atomic,
            hoy=lambda: FECHA,
        )
        self.periodo = PeriodoContable.objects.create(
            nombre="Junio 2026", fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 6, 30), estado=EstadoPeriodo.ABIERTO,
        )
        self.orden = self.ordenes.crear_orden(
            self.actor, nombre_juego="Neo Drift", fecha_inicio=FECHA,
        )
        self.programacion = Proceso.objects.get(nombre="Programación")
        self.arte = Proceso.objects.get(nombre="Arte")

    def cuenta(self, codigo):
        return Cuenta.objects.get(codigo=codigo)

    def mano_obra(self, horas="40", costo="20.00", proceso=None, **extra):
        return self.servicio.registrar_mano_obra(
            self.actor, orden_id=self.orden.pk, fecha=FECHA,
            proceso_id=(proceso or self.programacion).pk, horas=horas,
            costo_hora=costo, contrapartida_id=extra.get("contrapartida"),
            clave=extra.get("clave") or clave(),
        )

    def costo(self, elemento, importe, proceso=None, **extra):
        return self.servicio.registrar_costo(
            self.actor, elemento=elemento, orden_id=self.orden.pk,
            fecha=extra.get("fecha", FECHA),
            proceso_id=proceso.pk if proceso else None,
            descripcion=extra.get("descripcion", "Servicio"),
            importe=importe, contrapartida_id=extra.get("contrapartida"),
            clave=extra.get("clave") or clave(),
        )

    def movimientos(self, registro, tipo=AsientoCosto.TIPO_REGISTRO):
        asiento = registro.asientos.get(tipo=tipo)
        return {m.cuenta.codigo: m.importe for m in
                Movimiento.objects.filter(transaccion=asiento.transaccion)}

    def contrapartida_defecto(self, elemento):
        return ConfiguracionCuentaCosto.objects.get(
            elemento=elemento).contrapartida_defecto.codigo

    def total_vigente(self):
        return RegistroCosto.objects.filter(
            orden=self.orden, estado=RegistroCosto.ESTADO_VIGENTE,
        ).aggregate(t=Sum("importe"))["t"] or D("0")


class RegistroElementosTests(BaseCostos):
    def test_mano_obra_40_horas_por_20_es_800(self):
        registro = self.mano_obra()
        self.assertEqual(registro.importe, D("800.00"))
        haber = self.contrapartida_defecto(Elemento.MANO_OBRA)
        self.assertEqual(self.movimientos(registro),
                         {"4101": D("800.00"), haber: D("-800.00")})

    def test_costo_directo_1200(self):
        registro = self.costo(Elemento.DIRECTO, "1200.00")
        haber = self.contrapartida_defecto(Elemento.DIRECTO)
        self.assertEqual(self.movimientos(registro),
                         {"4102": D("1200.00"), haber: D("-1200.00")})

    def test_costo_indirecto_83_33_con_contrapartida_elegida(self):
        config = ConfiguracionCuentaCosto.objects.get(
            elemento=Elemento.INDIRECTO)
        elegida = config.contrapartidas.exclude(
            pk=config.contrapartida_defecto_id).first()
        registro = self.costo(Elemento.INDIRECTO, "83.33",
                              contrapartida=elegida.pk)
        self.assertEqual(self.movimientos(registro),
                         {"4103": D("83.33"), elegida.codigo: D("-83.33")})

    def test_total_de_los_tres_registros(self):
        self.mano_obra()
        self.costo(Elemento.DIRECTO, "1200.00")
        self.costo(Elemento.INDIRECTO, "83.33")
        self.assertEqual(self.total_vigente(), D("2083.33"))

    def test_asientos_cuadran_con_origen_y_clave(self):
        registros = [self.mano_obra(clave="mo-1"),
                     self.costo(Elemento.DIRECTO, "1200", clave="cd-1")]
        for registro in registros:
            asiento = registro.asientos.get()
            movimientos = Movimiento.objects.filter(
                transaccion=asiento.transaccion)
            self.assertEqual(sum(m.importe for m in movimientos), 0)
            self.assertTrue(all(f"OT-{self.orden.pk}" in m.referencia
                                for m in movimientos))
            self.assertEqual(asiento.orden, self.orden)
            self.assertEqual(asiento.registro, registro)
            self.assertEqual(asiento.clave_idempotencia,
                             registro.clave_idempotencia)
        self.assertEqual(
            sorted(a.clave_idempotencia for a in AsientoCosto.objects.all()),
            ["cd-1", "mo-1"],
        )

    def test_doble_envio_no_duplica(self):
        primero = self.mano_obra(clave="repetida")
        segundo = self.mano_obra(clave="repetida")
        self.assertEqual(primero.pk, segundo.pk)
        self.assertEqual(RegistroCosto.objects.count(), 1)
        self.assertEqual(AsientoCosto.objects.count(), 1)
        self.assertEqual(Movimiento.objects.count(), 2)

    def test_periodo_cerrado_rechaza_registro(self):
        PeriodoContable.objects.create(
            nombre="Mayo 2026", fecha_inicio=date(2026, 5, 1),
            fecha_fin=date(2026, 5, 31),
            estado=EstadoPeriodo.CIERRE_PROVISIONAL,
        )
        with self.assertRaises(PeriodoNoAbiertoError):
            self.costo(Elemento.DIRECTO, "100", fecha=date(2026, 5, 10))
        with self.assertRaises(PeriodoNoAbiertoError):
            self.costo(Elemento.DIRECTO, "100", fecha=date(2027, 1, 10))
        self.assertEqual(RegistroCosto.objects.count(), 0)
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_contrapartida_no_permitida_rechaza(self):
        with self.assertRaises(CuentaNoValidaError):
            self.costo(Elemento.DIRECTO, "100",
                       contrapartida=self.cuenta("4104").pk)
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_sin_configuracion_el_elemento_queda_bloqueado(self):
        ConfiguracionCuentaCosto.objects.filter(
            elemento=Elemento.INDIRECTO).delete()
        with self.assertRaises(ConfiguracionNoEncontradaError):
            self.costo(Elemento.INDIRECTO, "10")

    def test_orden_duplicada_por_juego(self):
        with self.assertRaises(OrdenDuplicadaError):
            self.ordenes.crear_orden(self.actor, nombre_juego="neo drift",
                                     fecha_inicio=FECHA)


class AnulacionTests(BaseCostos):
    def test_anular_crea_contra_asiento_y_baja_total(self):
        self.mano_obra()
        directo = self.costo(Elemento.DIRECTO, "1200.00")
        self.assertEqual(self.total_vigente(), D("2000.00"))
        self.servicio.anular(self.actor, registro_id=directo.pk,
                             motivo="Duplicado", clave="anula-1")
        directo.refresh_from_db()
        self.assertEqual(directo.estado, RegistroCosto.ESTADO_ANULADO)
        self.assertEqual(self.total_vigente(), D("800.00"))
        haber = self.contrapartida_defecto(Elemento.DIRECTO)
        self.assertEqual(
            self.movimientos(directo, AsientoCosto.TIPO_ANULACION),
            {"4102": D("-1200.00"), haber: D("1200.00")},
        )
        self.assertTrue(RegistroCosto.objects.filter(pk=directo.pk).exists())
        saldo_4102 = Movimiento.objects.filter(
            cuenta__codigo="4102").aggregate(t=Sum("importe"))["t"]
        self.assertEqual(saldo_4102, D("0.00"))

    def test_anular_dos_veces(self):
        registro = self.costo(Elemento.INDIRECTO, "83.33")
        self.servicio.anular(self.actor, registro_id=registro.pk,
                             motivo="Error", clave="a-1")
        self.servicio.anular(self.actor, registro_id=registro.pk,
                             motivo="Error", clave="a-1")
        self.assertEqual(AsientoCosto.objects.filter(
            tipo=AsientoCosto.TIPO_ANULACION).count(), 1)
        with self.assertRaises(RegistroYaAnuladoError):
            self.servicio.anular(self.actor, registro_id=registro.pk,
                                 motivo="Error", clave="a-2")

    def test_anulacion_exige_motivo_y_periodo_abierto(self):
        registro = self.costo(Elemento.DIRECTO, "10")
        with self.assertRaises(DatosInsuficientesError):
            self.servicio.anular(self.actor, registro_id=registro.pk,
                                 motivo=" ", clave="a-3")
        self.servicio._hoy = lambda: date(2027, 1, 1)
        with self.assertRaises(PeriodoNoAbiertoError):
            self.servicio.anular(self.actor, registro_id=registro.pk,
                                 motivo="Error", clave="a-4")
        registro.refresh_from_db()
        self.assertTrue(registro.vigente)


class CatalogoTests(BaseCostos):
    def test_configuracion_editable_desde_catalogo(self):
        catalogo = CatalogoCostosService(self.repo, None, transaction.atomic)
        bancos, proveedores = self.cuenta("1103"), self.cuenta("2101")
        catalogo.guardar_configuracion(
            self.actor, elemento=Elemento.MANO_OBRA,
            cuenta_costo=self.cuenta("4101"),
            contrapartidas=[bancos, proveedores],
            contrapartida_defecto=bancos,
        )
        registro = self.mano_obra()
        self.assertIn("1103", self.movimientos(registro))
        with self.assertRaises(CuentaNoValidaError):
            catalogo.guardar_configuracion(
                self.actor, elemento=Elemento.MANO_OBRA,
                cuenta_costo=self.cuenta("4101"),
                contrapartidas=[bancos],
                contrapartida_defecto=proveedores,
            )


class VistasCostosTests(BaseCostos):
    def setUp(self):
        super().setUp()
        self.actor.set_password("clave-segura-123")
        self.actor.save()
        self.client.force_login(self.actor)

    def test_doble_envio_del_formulario_no_duplica(self):
        url = reverse("costos_registro_nuevo",
                      args=[self.orden.pk, "directo"])
        datos = {"fecha": "2026-06-15", "descripcion": "Licencia motor",
                 "importe": "1200.00", "clave": "form-1",
                 "contrapartida": ConfiguracionCuentaCosto.objects.get(
                     elemento=Elemento.DIRECTO).contrapartida_defecto_id}
        for _ in range(2):
            respuesta = self.client.post(url, datos)
            self.assertRedirects(
                respuesta, reverse("costos_orden", args=[self.orden.pk]))
        self.assertEqual(RegistroCosto.objects.count(), 1)
        self.assertEqual(Movimiento.objects.count(), 2)

    def test_pantalla_y_modales(self):
        self.mano_obra()
        respuesta = self.client.get(reverse("costos_orden",
                                            args=[self.orden.pk]))
        self.assertContains(respuesta, "Mano de obra directa")
        self.assertContains(respuesta, "$800.00")
        for tipo in ("mano-obra", "directo", "indirecto"):
            modal = self.client.get(reverse(
                "costos_registro_nuevo", args=[self.orden.pk, tipo]))
            self.assertContains(modal, 'name="clave"')
            self.assertContains(modal, "data-costos-modal")

    def test_error_de_periodo_junto_al_campo(self):
        url = reverse("costos_registro_nuevo",
                      args=[self.orden.pk, "indirecto"])
        respuesta = self.client.post(url, {
            "fecha": "2030-01-01", "descripcion": "Luz", "importe": "10",
            "clave": "form-2",
            "contrapartida": ConfiguracionCuentaCosto.objects.get(
                elemento=Elemento.INDIRECTO).contrapartida_defecto_id,
        })
        self.assertContains(respuesta, "período contable")
        self.assertContains(respuesta, 'value="Luz"')
        self.assertEqual(RegistroCosto.objects.count(), 0)


class ConceptosEliminadosTests(SimpleTestCase):
    PROHIBIDOS = re.compile(
        r"cortes?_?costos|CorteCostos|corte provisional|costo_gestion|"
        r"costo de gesti[oó]n|afecta_mayor|fondo|equipo|"
        r"salario|sobreaplica|subaplica|reclasifica|doble conteo",
        re.IGNORECASE,
    )

    def test_modulo_sin_conceptos_eliminados(self):
        fuentes = [p for p in APP.rglob("*")
                   if p.suffix in {".py", ".html", ".js"}
                   and "migrations" not in p.parts
                   and "tests" not in p.parts]
        hallazgos = [
            f"{p.name}: {m.group(0)}" for p in fuentes
            for m in self.PROHIBIDOS.finditer(p.read_text("utf-8"))
        ]
        self.assertEqual(hallazgos, [])
