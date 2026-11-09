import secrets
from decimal import Decimal

from django.test import SimpleTestCase

from bitacora.eventos import Accion, Resultado
from catalogo.tests.fakes import BitacoraEnMemoria
from estados_financieros.exceptions import (
    BalanzaDescuadradaError,
    ConfirmacionIncorrectaError,
    ContrasenaIncorrectaError,
    GuardadoCierreError,
    MotivoObligatorioError,
    PeriodoNoAbiertoError,
    RecalculoPeriodoCerradoError,
)
from estados_financieros.exportadores import ExportadorEstadoPDF
from estados_financieros.formato import cifra
from estados_financieros.models import TipoEstado
from estados_financieros.services import (
    CierrePeriodoService,
    EstadosFinancierosService,
)
from libro_mayor.models import EstadoPeriodo
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol
from usuarios.tests.fakes import crear_usuario

from .fakes import EstadosRepositoryEnMemoria, periodo

CLAVE = secrets.token_urlsafe(12)
BALANCE = TipoEstado.BALANCE_GENERAL
RESULTADOS = TipoEstado.ESTADO_RESULTADOS


def importe(datos, texto):
    return next(f["importe"] for f in datos["filas"] if f["texto"] == texto)


class BaseTest(SimpleTestCase):
    def setUp(self):
        self.contador = crear_usuario("cont", Rol.CONTADOR_GENERAL)
        self.admin = crear_usuario("admin", Rol.ADMINISTRADOR)
        self.admin.set_password(CLAVE)
        self.periodo = periodo()
        self.repositorio = EstadosRepositoryEnMemoria([self.periodo])
        self.bitacora = BitacoraEnMemoria()
        self.estados = EstadosFinancierosService(
            self.repositorio, self.bitacora,
            ExportadorEstadoPDF(comprimir=False),
        )
        self.cierre = CierrePeriodoService(
            self.repositorio, self.estados, self.bitacora,
            self.repositorio.transaccion_simulada,
        )

    def cerrar(self, confirmacion="Ejercicio 2026", motivo="Fin de año"):
        return self.cierre.cerrar(self.contador, 1, confirmacion=confirmacion,
                                  motivo=motivo)

    def acciones(self):
        return [(r["accion"], r["resultado"]) for r in self.bitacora.registros]


class EstadosFinancierosTests(BaseTest):
    def test_balance_general_clasifica_y_cuadra(self):
        datos = self.estados.calcular(self.periodo, BALANCE)

        self.assertTrue(datos["cuadra"])
        self.assertEqual(datos["cubre"], "Al 31/12/2026")
        textos = [f["texto"] for f in datos["filas"] if f["clase"] == "grupo"]
        self.assertEqual(textos, ["Activo corriente", "Activo no corriente",
                                  "Pasivo corriente", "Pasivo no corriente"])
        self.assertEqual(importe(datos, "Total activo corriente"), "1500.00")
        self.assertEqual(importe(datos, "TOTAL ACTIVO"), "2200.00")
        self.assertEqual(importe(datos, "TOTAL PASIVO"), "700.00")
        self.assertEqual(
            importe(datos, "Utilidad (pérdida) del ejercicio"), "500.00"
        )
        self.assertEqual(importe(datos, "TOTAL PASIVO Y PATRIMONIO"),
                         "2200.00")
        self.assertEqual(importe(datos, "Cuenta 1203"), "-100.00")

    def test_estado_de_resultados_por_funcion(self):
        datos = self.estados.calcular(self.periodo, RESULTADOS)

        self.assertEqual(datos["cubre"], "Del 01/01/2026 al 31/12/2026")
        self.assertEqual(
            importe(datos, "Total ingresos de actividades ordinarias"),
            "1400.00",
        )
        self.assertEqual(importe(datos, "Utilidad (pérdida) bruta"),
                         "1100.00")
        self.assertEqual(importe(datos, "Utilidad (pérdida) de operación"),
                         "700.00")
        self.assertEqual(importe(
            datos, "Utilidad (pérdida) antes de impuesto sobre la renta"
        ), "650.00")
        self.assertEqual(importe(datos, "Utilidad (pérdida) del período"),
                         "500.00")

    def test_cifras_con_miles_y_negativos_entre_parentesis(self):
        self.assertEqual(cifra(Decimal("-1234.5")), "(1,234.50)")
        self.assertEqual(cifra("1234567.891"), "1,234,567.89")

    def test_periodo_cerrado_no_se_recalcula(self):
        self.periodo.estado = EstadoPeriodo.CIERRE_PROVISIONAL

        with self.assertRaises(RecalculoPeriodoCerradoError):
            self.estados.calcular(self.periodo, BALANCE)
        with self.assertRaisesMessage(RecalculoPeriodoCerradoError,
                                      "«Ejercicio 2026» está cerrado"):
            self.estados.generar_por_comando("Ejercicio 2026")
        self.assertEqual(self.repositorio.consultas_saldos, 0)
        self.assertEqual(self.acciones(),
                         [(Accion.EMISION_ESTADOS, Resultado.RECHAZADO)])

    def test_periodo_cerrado_se_consulta_desde_el_snapshot(self):
        self.cerrar()
        consultas = self.repositorio.consultas_saldos

        consulta = self.estados.obtener(self.admin, 1, BALANCE)
        archivo = self.estados.exportar_pdf(self.admin, 1, RESULTADOS)

        self.assertTrue(consulta.desde_snapshot)
        self.assertEqual(consulta.datos, self.repositorio.emitidos[0].datos)
        self.assertTrue(archivo.contenido.startswith(b"%PDF"))
        self.assertEqual(self.repositorio.consultas_saldos, consultas)
        self.assertIn("origen: snapshot",
                      self.bitacora.registros[-1]["detalle"])

    def test_pdf_con_encabezado_niif_y_balance_cuadrado(self):
        archivo = self.estados.exportar_pdf(self.contador, 1, BALANCE)

        self.assertEqual(archivo.nombre, "balance_general_20261231.pdf")
        for texto in (b"SunGames S.A. de C.V.", b"Estado de Situaci",
                      b"Al 31/12/2026", b"\\(USD\\)", b"TOTAL ACTIVO",
                      b"2,200.00", b"\\(100.00\\)", b"Patrimonio: cuadra",
                      b"Fecha de emisi", b"Abierto", b"NIC 1"):
            self.assertIn(texto, archivo.contenido)
        self.assertEqual(self.acciones(),
                         [(Accion.DESCARGA_ESTADO_PDF, Resultado.EXITOSO)])

    def test_usuario_sin_acceso_no_obtiene_estados(self):
        inactivo = crear_usuario("ina", Rol.CONTADOR_GENERAL, activo=False)

        with self.assertRaises(UsuarioInactivoError):
            self.estados.exportar_pdf(inactivo, 1, BALANCE)


class CierreTests(BaseTest):
    def assertSinCambios(self):
        self.assertEqual(self.periodo.estado, EstadoPeriodo.ABIERTO)
        self.assertEqual(self.repositorio.emitidos, [])

    def test_rechaza_nombre_de_confirmacion_incorrecto(self):
        with self.assertRaises(ConfirmacionIncorrectaError):
            self.cerrar(confirmacion="ejercicio 2026")
        self.assertSinCambios()
        self.assertEqual(self.acciones(),
                         [(Accion.CIERRE_PERIODO, Resultado.RECHAZADO)])

    def test_rechaza_sin_motivo(self):
        with self.assertRaises(MotivoObligatorioError):
            self.cerrar(motivo="   ")
        self.assertSinCambios()

    def test_rechaza_balanza_descuadrada(self):
        self.repositorio.suma = Decimal("12.50")

        with self.assertRaisesMessage(BalanzaDescuadradaError, "$12.50"):
            self.cerrar()
        self.assertSinCambios()

    def test_rechaza_periodo_no_abierto(self):
        self.periodo.estado = EstadoPeriodo.CIERRE_PROVISIONAL

        with self.assertRaises(PeriodoNoAbiertoError):
            self.cerrar()

    def test_solo_el_contador_general_cierra(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.cierre.cerrar(self.admin, 1, confirmacion="Ejercicio 2026",
                               motivo="x")

    def test_cierre_correcto_emite_snapshot_y_audita(self):
        self.cerrar()

        self.assertEqual(self.periodo.estado,
                         EstadoPeriodo.CIERRE_PROVISIONAL)
        self.assertEqual({e.tipo for e in self.repositorio.emitidos},
                         {BALANCE, RESULTADOS})
        self.assertEqual(self.acciones(), [
            (Accion.CIERRE_PERIODO, Resultado.EXITOSO),
            (Accion.EMISION_ESTADOS, Resultado.EXITOSO),
        ])
        registro = self.bitacora.registros[0]
        self.assertEqual(registro["actor"], self.contador)
        self.assertEqual(registro["referencia"], "Período Ejercicio 2026")
        self.assertEqual(registro["detalle"], "Motivo: Fin de año")

    def test_cierre_es_atomico(self):
        self.repositorio.fallar_al_cerrar = True

        with self.assertRaises(GuardadoCierreError):
            self.cerrar()
        self.assertSinCambios()
        self.assertEqual(self.bitacora.registros, [])


class ReaperturaTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.periodo.estado = EstadoPeriodo.CIERRE_PROVISIONAL

    def reabrir(self, actor=None, contrasena=CLAVE, motivo="Ajuste tardío"):
        return self.cierre.reabrir(actor or self.admin, 1,
                                   contrasena=contrasena, motivo=motivo)

    def test_no_administrador_no_reabre(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.reabrir(self.contador)
        self.assertTrue(self.periodo.cerrado)
        self.assertEqual(self.acciones(),
                         [(Accion.REAPERTURA_PERIODO, Resultado.RECHAZADO)])

    def test_contrasena_incorrecta_se_audita_sin_la_contrasena(self):
        intento = "otra-" + CLAVE

        with self.assertRaises(ContrasenaIncorrectaError):
            self.reabrir(contrasena=intento)
        self.assertTrue(self.periodo.cerrado)
        self.assertEqual(self.acciones(), [
            (Accion.REAPERTURA_PERIODO, Resultado.CREDENCIALES_INCORRECTAS)
        ])
        self.assertNotIn(intento, str(self.bitacora.registros))

    def test_exige_motivo(self):
        with self.assertRaises(MotivoObligatorioError):
            self.reabrir(motivo="")
        self.assertTrue(self.periodo.cerrado)

    def test_reapertura_correcta(self):
        self.reabrir()

        self.assertEqual(self.periodo.estado, EstadoPeriodo.ABIERTO)
        self.assertEqual(self.acciones(),
                         [(Accion.REAPERTURA_PERIODO, Resultado.EXITOSO)])
        self.assertEqual(self.bitacora.registros[0]["detalle"],
                         "Motivo: Ajuste tardío")
        self.assertNotIn(CLAVE, str(self.bitacora.registros))
