import datetime
from decimal import Decimal

from django.test import SimpleTestCase

from bitacora.eventos import Accion
from libro_mayor.exceptions import (
    CampoObligatorioError,
    ConceptoInvalidoError,
    CuentaNoRegistrableError,
    CuentaRepetidaError,
    FechaInvalidaError,
    GuardadoTransaccionError,
    MovimientoInvalidoError,
    PeriodoCerradoError,
    TransaccionDescuadradaError,
)
from libro_mayor.services import ConfiguracionLibroMayor, LibroMayorService
from usuarios.exceptions import RolNoAutorizadoError
from usuarios.roles import Rol
from usuarios.tests.fakes import crear_usuario

from catalogo.tests.fakes import BitacoraEnMemoria

from .fakes import ACREEDORA, TransaccionRepositoryEnMemoria, cuenta, periodo

FECHA = datetime.date(2026, 11, 3)


def mov(codigo, importe):
    return {"cuenta": codigo, "importe": importe}


class LibroMayorTestCase(SimpleTestCase):
    def setUp(self):
        self.contador = crear_usuario("cont", Rol.CONTADOR_GENERAL)
        self.caja = cuenta("1101")
        self.ventas = cuenta("5101", ACREEDORA)
        self.iva = cuenta("2103", ACREEDORA)
        self.repositorio = TransaccionRepositoryEnMemoria(
            cuentas=[
                self.caja, self.ventas, self.iva,
                cuenta("1102", activa=False), cuenta("1103"),
            ],
            periodos=[
                periodo(datetime.date(2026, 1, 1), datetime.date(2026, 10, 31),
                        cerrado=True),
                periodo(datetime.date(2026, 11, 1),
                        datetime.date(2026, 12, 31)),
            ],
            con_subcuentas=["1103"],
        )
        self.bitacora = BitacoraEnMemoria()
        self.servicio = LibroMayorService(
            self.repositorio, self.bitacora, ConfiguracionLibroMayor(),
            self.repositorio.transaccion_simulada,
        )

    def registrar(self, movimientos, fecha=FECHA, concepto="Venta del día"):
        return self.servicio.registrar(
            self.contador, fecha=fecha, concepto=concepto,
            movimientos=movimientos,
        )

    def assertNadaGuardado(self):
        self.assertEqual(self.repositorio.transacciones, [])
        self.assertEqual(self.repositorio.guardados, [])
        self.assertEqual(self.bitacora.registros, [])


class RegistrarTransaccionTest(LibroMayorTestCase):
    def test_tres_cuentas_que_suman_cero_se_guardan(self):
        transaccion = self.registrar([
            mov("1101", "113.00"), mov("5101", "-100.00"),
            mov("2103", "-13.00"),
        ])

        self.assertEqual(len(self.repositorio.guardados), 3)
        self.assertEqual(
            [m.importe for m in self.repositorio.guardados],
            [Decimal("113.00"), Decimal("-100.00"), Decimal("-13.00")],
        )
        self.assertEqual(self.bitacora.registros[0]["accion"],
                         Accion.REGISTRO_TRANSACCION)
        self.assertEqual(self.bitacora.registros[0]["referencia"],
                         f"Transacción {transaccion.pk}")

    def test_descuadrada_se_rechaza_con_la_diferencia(self):
        with self.assertRaises(TransaccionDescuadradaError) as ctx:
            self.registrar([mov("1101", "100.00"), mov("5101", "-90.00")])

        self.assertEqual(ctx.exception.diferencia, Decimal("10.00"))
        self.assertIn("10.00", str(ctx.exception))
        self.assertNadaGuardado()

    def test_un_solo_movimiento_se_rechaza(self):
        with self.assertRaises(MovimientoInvalidoError):
            self.registrar([mov("1101", "0.01")])
        self.assertNadaGuardado()

    def test_maximo_de_movimientos_configurable(self):
        self.servicio = LibroMayorService(
            self.repositorio, self.bitacora,
            ConfiguracionLibroMayor(max_movimientos=2),
        )
        with self.assertRaises(MovimientoInvalidoError):
            self.registrar([
                mov("1101", "2"), mov("5101", "-1"), mov("2103", "-1")
            ])

    def test_misma_cuenta_dos_veces_senala_las_lineas(self):
        with self.assertRaises(CuentaRepetidaError) as ctx:
            self.registrar([
                mov("1101", "10"), mov("5101", "-20"), mov("1101", "10")
            ])
        self.assertEqual(ctx.exception.lineas, (0, 2))
        self.assertNadaGuardado()

    def test_importe_cero_se_rechaza(self):
        with self.assertRaises(MovimientoInvalidoError) as ctx:
            self.registrar([mov("1101", "0.00"), mov("5101", "0")])
        self.assertEqual(ctx.exception.linea, 0)

    def test_importes_invalidos(self):
        for importe in ("12.345", "abc", "NaN", "Infinity", "1e15"):
            with self.subTest(importe=importe):
                with self.assertRaises(MovimientoInvalidoError):
                    self.registrar([mov("1101", importe), mov("5101", "-1")])
        self.assertNadaGuardado()

    def test_cada_campo_vacio_se_rechaza(self):
        casos = [
            ({"fecha": None}, "fecha", None),
            ({"concepto": "   "}, "concepto", None),
            ({"movimientos": [mov(" ", "1"), mov("5101", "-1")]},
             "cuenta", 0),
            ({"movimientos": [mov("1101", "1"), mov("5101", "  ")]},
             "importe", 1),
        ]
        for cambios, campo, linea in casos:
            with self.subTest(campo=campo):
                datos = {
                    "fecha": FECHA, "concepto": "Venta",
                    "movimientos": [mov("1101", "1"), mov("5101", "-1")],
                    **cambios,
                }
                with self.assertRaises(CampoObligatorioError) as ctx:
                    self.servicio.registrar(self.contador, **datos)
                self.assertEqual(ctx.exception.campo, campo)
                self.assertEqual(ctx.exception.linea, linea)
        self.assertNadaGuardado()

    def test_cuenta_inactiva_inexistente_o_con_subcuentas_se_rechaza(self):
        for codigo in ("1102", "9999", "1103"):
            with self.subTest(codigo=codigo):
                with self.assertRaises(CuentaNoRegistrableError) as ctx:
                    self.registrar([mov("1101", "5"), mov(codigo, "-5")])
                self.assertEqual(ctx.exception.linea, 1)
        self.assertNadaGuardado()

    def test_periodo_cerrado_y_fecha_fuera_del_ejercicio(self):
        lineas = [mov("1101", "5"), mov("5101", "-5")]
        with self.assertRaises(PeriodoCerradoError):
            self.registrar(lineas, fecha=datetime.date(2026, 10, 31))
        with self.assertRaises(FechaInvalidaError):
            self.registrar(lineas, fecha=datetime.date(2027, 1, 1))
        self.assertNadaGuardado()

    def test_concepto_con_longitud_o_caracteres_invalidos(self):
        lineas = [mov("1101", "5"), mov("5101", "-5")]
        for concepto in ("ab", "x" * 201, "Venta\x07 del día"):
            with self.subTest(concepto=concepto[:10]):
                with self.assertRaises(ConceptoInvalidoError):
                    self.registrar(lineas, concepto=concepto)

    def test_solo_el_contador_general_registra(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.registrar(
                crear_usuario("admin"), fecha=FECHA, concepto="Venta",
                movimientos=[mov("1101", "5"), mov("5101", "-5")],
            )
        self.assertNadaGuardado()

    def test_si_falla_el_ultimo_movimiento_no_queda_nada(self):
        self.repositorio.fallar_en_movimiento = 3

        with self.assertRaises(GuardadoTransaccionError):
            self.registrar([
                mov("1101", "113"), mov("5101", "-100"), mov("2103", "-13")
            ])
        self.assertNadaGuardado()

    def test_decimal_sin_errores_de_redondeo(self):
        self.assertEqual(
            Decimal("0.1") + Decimal("0.2") - Decimal("0.3"), Decimal("0")
        )
        self.registrar([
            mov("1101", Decimal("0.1")), mov("2103", "0.2"),
            mov("5101", "-0.3"),
        ])
        self.assertEqual(len(self.repositorio.guardados), 3)

    def test_rechaza_importes_que_no_son_decimal_ni_texto(self):
        with self.assertRaises(MovimientoInvalidoError):
            self.registrar([mov("1101", 0.5), mov("5101", "-0.5")])


class SaldosTest(LibroMayorTestCase):
    def setUp(self):
        super().setUp()
        self.registrar([mov("1101", "113.00"), mov("5101", "-100.00"),
                        mov("2103", "-13.00")])
        self.registrar([mov("1101", "-20.00"), mov("5101", "20.00")],
                       fecha=datetime.date(2026, 11, 20))

    def test_saldo_a_fecha_de_corte(self):
        saldo = self.servicio.saldo(
            self.contador, "1101", datetime.date(2026, 11, 10)
        )
        self.assertEqual(saldo.saldo, Decimal("113.00"))
        self.assertEqual(saldo.sentido, "Deudor")

        saldo = self.servicio.saldo(
            self.contador, "1101", datetime.date(2026, 11, 30)
        )
        self.assertEqual(saldo.cargos, Decimal("113.00"))
        self.assertEqual(saldo.abonos, Decimal("-20.00"))
        self.assertEqual(saldo.saldo, Decimal("93.00"))

    def test_naturaleza_solo_cambia_la_presentacion(self):
        saldo = self.servicio.saldo(
            self.contador, "5101", datetime.date(2026, 11, 30)
        )
        self.assertEqual(saldo.saldo, Decimal("-80.00"))
        self.assertEqual(saldo.saldo_presentado, Decimal("80.00"))
        self.assertEqual(saldo.sentido, "Acreedor")

    def test_sin_movimientos_el_saldo_es_cero(self):
        saldo = self.servicio.saldo(
            self.contador, "1102", datetime.date(2026, 11, 30)
        )
        self.assertEqual(saldo.saldo, Decimal("0.00"))

    def test_consulta_con_saldo_acumulado(self):
        consulta = self.servicio.consultar(
            self.contador, "1101", desde=datetime.date(2026, 11, 10)
        )
        self.assertEqual(consulta.saldo_inicial, Decimal("113.00"))
        self.assertEqual(
            [linea.saldo for linea in consulta.lineas], [Decimal("93.00")]
        )

    def test_rango_invertido(self):
        with self.assertRaises(FechaInvalidaError):
            self.servicio.consultar(
                self.contador, "1101", desde=datetime.date(2026, 12, 1),
                hasta=datetime.date(2026, 11, 1),
            )
