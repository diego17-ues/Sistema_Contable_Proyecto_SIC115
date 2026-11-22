from datetime import date
from decimal import Decimal

from django.test import TestCase

from bitacora.models import RegistroBitacora
from estimacion.composition import crear_estimacion_service
from estimacion.exceptions import (
    EstimacionDuplicadaError,
    EstimacionInvalidaError,
    ParametroInvalidoError,
    ParametroNoEncontradoError,
    RondaCerradaError,
    RolNoEncontradoError,
)
from estimacion.models import EstimacionExperto, Rol as RolEstimacion
from usuarios.exceptions import RolNoAutorizadoError
from usuarios.models import Usuario
from usuarios.roles import Rol

FECHA = date(2026, 6, 1)


class DelphiTests(TestCase):
    def setUp(self):
        self.servicio = crear_estimacion_service()
        self.admin = Usuario.objects.create(
            username="admin", nombre_completo="Admin",
            rol=Rol.ADMINISTRADOR,
        )
        self.contador = Usuario.objects.create(
            username="costos", nombre_completo="Costos",
            rol=Rol.CONTADOR_COSTOS,
        )
        self.general = Usuario.objects.create(
            username="general", nombre_completo="General",
            rol=Rol.CONTADOR_GENERAL,
        )
        self.rol = RolEstimacion.objects.create(
            nombre="Programador", nivel=3
        )
        self.experto1 = self.servicio.crear_experto(
            self.admin, "Experto Uno"
        )
        self.experto2 = self.servicio.crear_experto(
            self.admin, "Experto Dos"
        )
        self.juego = self.servicio.crear_juego(self.admin, "Proyecto A")
        self.fase = self.juego.fases.get(nombre="Programación")

    def test_juego_crea_fases_fijas(self):
        fases = list(self.juego.fases.all())
        self.assertEqual(len(fases), 7)
        self.assertEqual(
            [f.orden for f in fases], list(range(1, 8))
        )
        self.assertEqual(fases[0].nombre, "Dirección de producto / productor")
        self.assertEqual(fases[0].clasificacion, "MIXTO")
        self.assertEqual(fases[1].clasificacion, "CAPEX")
        self.assertEqual(fases[2].clasificacion, "CAPEX")
        self.assertEqual(fases[3].clasificacion, "OPEX")
        self.assertEqual(fases[6].nombre, "Localización")

    def estimacion(self, experto, o, m, p, ronda=1):
        return self.servicio.registrar_estimacion(
            self.admin, juego_id=self.juego.pk, fase_id=self.fase.pk,
            rol_id=self.rol.pk, experto_id=experto.pk, ronda=ronda,
            optimista=Decimal(str(o)), moda=Decimal(str(m)),
            pesimista=Decimal(str(p)),
        )

    def matriz(self, experto, ronda=1):
        matriz = {
            fase.pk: {
                "optimista": Decimal("10"),
                "moda": Decimal("20"),
                "pesimista": Decimal("30"),
            }
            for fase in self.juego.fases.all()
        }
        return self.servicio.registrar_estimacion_matriz(
            self.admin, juego_id=self.juego.pk, rol_id=self.rol.pk,
            experto_id=experto.pk, ronda=ronda, matriz=matriz,
        )

    def test_flujo_delphi_completo(self):
        self.estimacion(self.experto1, 80, 100, 120)
        self.estimacion(self.experto2, 180, 200, 220)

        consolidado = self.servicio.consolidar(
            self.admin, self.juego.pk, 1, fecha=FECHA
        )
        self.assertEqual(len(consolidado), 1)
        grupo = consolidado[0]
        self.assertEqual(grupo["expertos"], 2)
        # E1 = 100, E2 = 200 → media 150, mediana 150, cv = 50/150
        self.assertAlmostEqual(float(grupo["media"]), 150, delta=0.001)
        self.assertAlmostEqual(float(grupo["mediana"]), 150, delta=0.001)
        self.assertAlmostEqual(
            float(grupo["coeficiente_variacion"]), 0.3333, delta=0.001
        )
        self.assertTrue(grupo["requiere_nueva_ronda"])

    def test_cv_bajo_no_marca_nueva_ronda(self):
        self.estimacion(self.experto1, 98, 100, 102)
        self.estimacion(self.experto2, 100, 102, 104)
        consolidado = self.servicio.consolidar(
            self.admin, self.juego.pk, 1, fecha=FECHA
        )
        grupo = consolidado[0]
        self.assertLess(
            float(grupo["coeficiente_variacion"]), 0.20
        )
        self.assertFalse(grupo["requiere_nueva_ronda"])

    def test_cerrar_ronda_registra_aprobacion(self):
        self.estimacion(self.experto1, 100, 120, 140)
        ronda = self.servicio.cerrar_ronda(
            self.contador, self.juego.pk, 1, fecha=FECHA
        )
        self.assertTrue(ronda.cerrada)
        self.assertEqual(ronda.aprobada_por, self.contador)
        self.assertIsNotNone(ronda.resultado)
        evento = RegistroBitacora.objects.get(
            accion="CIERRE_RONDA_DELPHI"
        )
        self.assertEqual(evento.actor, self.contador)

    def test_ronda_cerrada_no_admite_estimaciones(self):
        self.estimacion(self.experto1, 100, 120, 140)
        self.servicio.cerrar_ronda(
            self.admin, self.juego.pk, 1, fecha=FECHA
        )
        with self.assertRaises(RondaCerradaError):
            self.estimacion(self.experto2, 100, 120, 140)

    def test_ronda_cerrada_no_se_vuelve_a_cerrar(self):
        self.estimacion(self.experto1, 100, 120, 140)
        self.servicio.cerrar_ronda(
            self.admin, self.juego.pk, 1, fecha=FECHA
        )
        with self.assertRaises(RondaCerradaError):
            self.servicio.cerrar_ronda(
                self.admin, self.juego.pk, 1, fecha=FECHA
            )

    def test_matriz_registra_todas_las_fases(self):
        creadas = self.matriz(self.experto1)
        self.assertEqual(len(creadas), 7)
        self.assertEqual(
            EstimacionExperto.objects.filter(juego=self.juego).count(), 7
        )
        self.assertTrue(
            all(e.ronda == 1 for e in creadas)
        )

    def test_matriz_duplicada_rechazada(self):
        self.matriz(self.experto1)
        with self.assertRaises(EstimacionDuplicadaError):
            self.matriz(self.experto1)

    def test_matriz_ronda_cerrada_rechazada(self):
        self.matriz(self.experto1)
        self.servicio.cerrar_ronda(
            self.admin, self.juego.pk, 1, fecha=FECHA
        )
        with self.assertRaises(RondaCerradaError):
            self.matriz(self.experto2)

    def test_estimacion_invalida_rechazada(self):
        with self.assertRaises(EstimacionInvalidaError):
            self.servicio.registrar_estimacion(
                self.admin, juego_id=self.juego.pk, fase_id=self.fase.pk,
                rol_id=self.rol.pk, experto_id=self.experto1.pk,
                ronda=1, optimista=Decimal("500"),
                moda=Decimal("400"), pesimista=Decimal("300"),
            )

    def test_estimacion_experta_se_puede_editar_en_ronda_abierta(self):
        estimacion = self.estimacion(self.experto1, 10, 20, 30)

        actualizada = self.servicio.actualizar_estimacion(
            self.admin, self.juego.pk, estimacion.pk,
            optimista=Decimal("12"), moda=Decimal("24"),
            pesimista=Decimal("36"), justificacion="Revisada",
        )

        self.assertEqual(actualizada.optimista, Decimal("12"))
        self.assertEqual(actualizada.moda, Decimal("24"))
        self.assertEqual(actualizada.pesimista, Decimal("36"))
        self.assertEqual(actualizada.justificacion, "Revisada")

    def test_baja_logica_de_estimacion_conserva_y_permite_restaurar(self):
        estimacion = self.estimacion(self.experto1, 10, 20, 30)

        archivada = self.servicio.eliminar_estimacion(
            self.admin, self.juego.pk, estimacion.pk
        )

        self.assertTrue(archivada.eliminada)
        self.assertEqual(archivada.eliminado_por, self.admin)
        self.assertTrue(EstimacionExperto.objects.filter(
            pk=estimacion.pk
        ).exists())
        self.assertEqual(
            list(self.servicio.estimaciones(self.admin, self.juego.pk)), []
        )
        archivadas = list(self.servicio.estimaciones(
            self.admin, self.juego.pk, incluir_eliminadas=True
        ))
        self.assertEqual(len(archivadas), 1)

        restaurada = self.servicio.restaurar_estimacion(
            self.admin, self.juego.pk, estimacion.pk
        )
        self.assertFalse(restaurada.eliminada)
        self.assertEqual(
            len(list(self.servicio.estimaciones(
                self.admin, self.juego.pk
            ))),
            1,
        )

    def test_estimacion_archivada_puede_reemplazarse_y_no_restaurarse_duplicada(self):
        archivada = self.estimacion(self.experto1, 10, 20, 30)
        self.servicio.eliminar_estimacion(
            self.admin, self.juego.pk, archivada.pk
        )
        nueva = self.estimacion(self.experto1, 11, 21, 31)

        self.assertNotEqual(archivada.pk, nueva.pk)
        with self.assertRaises(EstimacionDuplicadaError):
            self.servicio.restaurar_estimacion(
                self.admin, self.juego.pk, archivada.pk
            )

    def test_estimacion_de_ronda_cerrada_no_se_edita_ni_archiva(self):
        estimacion = self.estimacion(self.experto1, 10, 20, 30)
        self.servicio.cerrar_ronda(
            self.admin, self.juego.pk, 1, fecha=FECHA
        )

        with self.assertRaises(RondaCerradaError):
            self.servicio.actualizar_estimacion(
                self.admin, self.juego.pk, estimacion.pk,
                optimista=Decimal("12"), moda=Decimal("24"),
                pesimista=Decimal("36"),
            )
        with self.assertRaises(RondaCerradaError):
            self.servicio.eliminar_estimacion(
                self.admin, self.juego.pk, estimacion.pk
            )

    def test_contador_general_no_accede(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.listar_juegos(self.general)
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.crear_juego(self.general, "X")

    def test_contador_costos_si_accede(self):
        juegos = self.servicio.listar_juegos(self.contador)
        self.assertEqual(list(juegos), [self.juego])

    def test_parametro_traslapado_rechazado(self):
        self.servicio.crear_parametro(
            self.admin, "tasa_extra", Decimal("0.1"),
            date(2026, 1, 1), date(2026, 6, 30),
        )
        with self.assertRaises(ParametroInvalidoError):
            self.servicio.crear_parametro(
                self.admin, "tasa_extra", Decimal("0.2"),
                date(2026, 3, 1), date(2026, 12, 31),
            )
        # Sin traslape: vigente después del cierre de la anterior.
        self.servicio.crear_parametro(
            self.admin, "tasa_extra", Decimal("0.2"),
            date(2026, 7, 1), None,
        )

    def test_actualizar_parametro(self):
        parametro = self.servicio.crear_parametro(
            self.admin, "tasa_extra", Decimal("0.1"),
            date(2026, 1, 1), date(2026, 6, 30),
        )
        siguiente = self.servicio.crear_parametro(
            self.admin, "tasa_extra", Decimal("0.5"),
            date(2026, 7, 1), None,
        )
        actualizado = self.servicio.actualizar_parametro(
            self.admin, parametro.pk, valor=Decimal("0.3"),
            vigente_desde=date(2026, 2, 1),
            vigente_hasta=date(2026, 5, 31),
            verificado=True,
        )
        self.assertEqual(actualizado.valor, Decimal("0.300000"))
        self.assertEqual(actualizado.clave, "tasa_extra")
        self.assertTrue(actualizado.verificado)
        # Traslapar otra vigencia del mismo parámetro se rechaza.
        with self.assertRaises(ParametroInvalidoError):
            self.servicio.actualizar_parametro(
                self.admin, siguiente.pk, valor=Decimal("0.9"),
                vigente_desde=date(2026, 3, 1),
            )
        # Parámetro inexistente.
        with self.assertRaises(ParametroNoEncontradoError):
            self.servicio.actualizar_parametro(
                self.admin, 9999, valor=Decimal("1"),
                vigente_desde=date(2026, 1, 1),
            )
        # Rol sin acceso no modifica.
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.actualizar_parametro(
                self.general, parametro.pk, valor=Decimal("0.9"),
                vigente_desde=date(2026, 1, 1),
            )
