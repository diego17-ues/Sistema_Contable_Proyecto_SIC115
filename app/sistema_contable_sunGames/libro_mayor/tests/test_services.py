import datetime
from decimal import Decimal

from django.test import SimpleTestCase

from bitacora.eventos import Accion
from libro_mayor.exceptions import (
    CampoObligatorioError,
    ConceptoInvalidoError,
    CuentaNoRegistrableError,
    FechaInvalidaError,
    GuardadoTransaccionError,
    MovimientoInvalidoError,
    PeriodoCerradoError,
)
from libro_mayor.exportadores import ExportadorBalancePDF
from libro_mayor.services import ConfiguracionLibroMayor, LibroMayorService
from usuarios.exceptions import RolNoAutorizadoError
from usuarios.roles import Rol
from usuarios.tests.fakes import crear_usuario

from catalogo.tests.fakes import BitacoraEnMemoria

from .fakes import ACREEDORA, TransaccionRepositoryEnMemoria, cuenta, periodo

FECHA = datetime.date(2026, 11, 3)


def linea(debe="", haber="", fecha=FECHA, concepto="Venta del día",
          referencia="V-1", tipo="COMPROBANTE_INGRESO"):
    return {
        "fecha": fecha, "concepto": concepto, "referencia": referencia,
        "tipo": tipo, "debe": debe, "haber": haber,
    }


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

    def registrar(self, codigo, lineas):
        return self.servicio.registrar(
            self.contador, cuenta=codigo, movimientos=lineas
        )

    def assertNadaGuardado(self):
        self.assertEqual(self.repositorio.transacciones, [])
        self.assertEqual(self.repositorio.guardados, [])
        self.assertEqual(self.bitacora.registros, [])


class RegistrarMovimientosTest(LibroMayorTestCase):
    def test_debe_positivo_y_haber_negativo(self):
        transaccion = self.registrar(
            "1101", [linea(debe="113.00"), linea(haber="20.50")]
        )

        self.assertEqual(
            [m.importe for m in self.repositorio.guardados],
            [Decimal("113.00"), Decimal("-20.50")],
        )
        self.assertTrue(
            all(m.cuenta is self.caja for m in self.repositorio.guardados)
        )
        registro = self.bitacora.registros[0]
        self.assertEqual(registro["accion"], Accion.REGISTRO_TRANSACCION)
        self.assertEqual(
            registro["referencia"],
            f"Transacción {transaccion.pk} · cuenta 1101 · 2 movimiento(s)",
        )

    def test_no_exige_que_los_movimientos_cuadren(self):
        self.registrar("1101", [linea(debe="100.00")])
        self.registrar("5101", [linea(haber="90.00")])

        self.assertEqual(len(self.repositorio.guardados), 2)
        self.assertEqual(len(self.repositorio.transacciones), 2)

    def test_un_solo_movimiento_se_guarda_y_ninguno_se_rechaza(self):
        self.registrar("1101", [linea(debe="0.01")])
        self.assertEqual(len(self.repositorio.guardados), 1)
        with self.assertRaises(MovimientoInvalidoError):
            self.registrar("1101", [])

    def test_maximo_de_movimientos_configurable(self):
        self.servicio = LibroMayorService(
            self.repositorio, self.bitacora,
            ConfiguracionLibroMayor(max_movimientos=2),
        )
        with self.assertRaises(MovimientoInvalidoError):
            self.registrar("1101", [linea(debe="1")] * 3)

    def test_monto_en_debe_o_en_haber_pero_no_en_ambos(self):
        with self.assertRaises(CampoObligatorioError) as ctx:
            self.registrar("1101", [linea(debe="5"), linea()])
        self.assertEqual((ctx.exception.campo, ctx.exception.linea),
                         ("debe", 1))
        with self.assertRaises(MovimientoInvalidoError) as ctx:
            self.registrar("1101", [linea(debe="5", haber="5")])
        self.assertEqual(ctx.exception.campo, "haber")
        self.assertNadaGuardado()

    def test_montos_invalidos(self):
        casos = ("0", "0.00", "-5", "12.345", "abc", "NaN", "Infinity",
                 "1e15")
        for monto in casos:
            for campo in ("debe", "haber"):
                with self.subTest(monto=monto, campo=campo):
                    with self.assertRaises(MovimientoInvalidoError) as ctx:
                        self.registrar("1101", [linea(**{campo: monto})])
                    self.assertEqual(ctx.exception.campo, campo)
        self.assertNadaGuardado()

    def test_cada_campo_vacio_se_rechaza(self):
        for campo in ("fecha", "concepto", "tipo"):
            with self.subTest(campo=campo):
                vacio = None if campo == "fecha" else "   "
                with self.assertRaises(CampoObligatorioError) as ctx:
                    self.registrar(
                        "1101", [linea(debe="1"),
                                 linea(debe="1", **{campo: vacio})]
                    )
                self.assertEqual(ctx.exception.campo, campo)
                self.assertEqual(ctx.exception.linea, 1)
        with self.assertRaises(CampoObligatorioError) as ctx:
            self.registrar(" ", [linea(debe="1")])
        self.assertEqual(ctx.exception.campo, "cuenta")
        self.assertNadaGuardado()

    def test_referencia_opcional_con_limites(self):
        self.registrar("1101", [linea(debe="1", referencia="")])
        with self.assertRaises(MovimientoInvalidoError):
            self.registrar("1101", [linea(debe="1", referencia="x" * 41)])

    def test_tipo_desconocido_se_rechaza(self):
        with self.assertRaises(MovimientoInvalidoError) as ctx:
            self.registrar("1101", [linea(debe="1", tipo="OTRO")])
        self.assertEqual(ctx.exception.campo, "tipo")

    def test_cuenta_inactiva_inexistente_o_con_subcuentas_se_rechaza(self):
        for codigo in ("1102", "9999", "1103"):
            with self.subTest(codigo=codigo):
                with self.assertRaises(CuentaNoRegistrableError) as ctx:
                    self.registrar(codigo, [linea(debe="5")])
                self.assertEqual(ctx.exception.campo, "cuenta")
        self.assertNadaGuardado()

    def test_periodo_cerrado_y_fecha_fuera_del_ejercicio(self):
        with self.assertRaises(PeriodoCerradoError) as ctx:
            self.registrar("1101", [
                linea(debe="5"),
                linea(debe="5", fecha=datetime.date(2026, 10, 31)),
            ])
        self.assertEqual(ctx.exception.linea, 1)
        with self.assertRaises(FechaInvalidaError):
            self.registrar(
                "1101", [linea(debe="5", fecha=datetime.date(2027, 1, 1))]
            )
        self.assertNadaGuardado()

    def test_descripcion_con_longitud_o_caracteres_invalidos(self):
        for concepto in ("ab", "x" * 201, "Venta\x07 del día"):
            with self.subTest(concepto=concepto[:10]):
                with self.assertRaises(ConceptoInvalidoError):
                    self.registrar(
                        "1101", [linea(debe="5", concepto=concepto)]
                    )

    def test_solo_el_contador_general_registra(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.registrar(
                crear_usuario("admin"), cuenta="1101",
                movimientos=[linea(debe="5")],
            )
        self.assertNadaGuardado()

    def test_si_falla_el_ultimo_movimiento_no_queda_nada(self):
        self.repositorio.fallar_en_movimiento = 3

        with self.assertRaises(GuardadoTransaccionError):
            self.registrar("1101", [
                linea(debe="113"), linea(haber="100"), linea(haber="13")
            ])
        self.assertNadaGuardado()

    def test_decimal_sin_errores_de_redondeo(self):
        self.assertEqual(
            Decimal("0.1") + Decimal("0.2") - Decimal("0.3"), Decimal("0")
        )
        self.registrar("1101", [
            linea(debe=Decimal("0.1")), linea(debe="0.2"), linea(haber="0.3")
        ])
        saldo = self.servicio.saldo(self.contador, "1101", FECHA)
        self.assertEqual(saldo.saldo, Decimal("0"))
        self.assertEqual(saldo.sentido, "Saldado")

    def test_rechaza_montos_que_no_son_decimal_ni_texto(self):
        with self.assertRaises(MovimientoInvalidoError):
            self.registrar("1101", [linea(debe=0.5)])


class SaldosTest(LibroMayorTestCase):
    def setUp(self):
        super().setUp()
        self.registrar("1101", [linea(debe="113.00")])
        self.registrar("5101", [linea(haber="100.00")])
        self.registrar("2103", [linea(haber="13.00")])
        self.registrar("1101", [
            linea(haber="20.00", fecha=datetime.date(2026, 11, 20),
                  tipo="COMPROBANTE_EGRESO"),
        ])

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
        self.assertEqual(saldo.saldo, Decimal("-100.00"))
        self.assertEqual(saldo.saldo_presentado, Decimal("100.00"))
        self.assertEqual(saldo.sentido, "Acreedor")

    def test_sin_movimientos_el_saldo_es_cero(self):
        saldo = self.servicio.saldo(
            self.contador, "1102", datetime.date(2026, 11, 30)
        )
        self.assertEqual(saldo.saldo, Decimal("0.00"))

    def test_consulta_con_debe_haber_saldo_y_correlativo(self):
        consulta = self.servicio.consultar(self.contador, "1101")
        primera, segunda = consulta.lineas
        self.assertEqual((primera.debe, primera.haber),
                         (Decimal("113.00"), None))
        self.assertEqual((segunda.debe, segunda.haber),
                         (None, Decimal("20.00")))
        self.assertEqual(segunda.saldo, Decimal("93.00"))
        self.assertEqual(primera.correlativo,
                         "Comprobante de Ingreso-2026-00001")
        self.assertEqual(segunda.correlativo,
                         "Comprobante de Egreso-2026-00001")

    def test_consulta_desde_arrastra_saldo_anterior(self):
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


class BalanceComprobacionTest(LibroMayorTestCase):
    def test_solo_cuentas_con_movimientos_y_diferencia_sin_bloqueo(self):
        self.registrar("1101", [linea(debe="113.00")])
        self.registrar("5101", [linea(haber="100.00")])

        balance = self.servicio.balance_comprobacion(self.contador, FECHA)

        self.assertEqual(
            [fila.cuenta.codigo for fila in balance.filas], ["1101", "5101"]
        )
        self.assertEqual(balance.total_debe, Decimal("113.00"))
        self.assertEqual(balance.total_haber, Decimal("100.00"))
        self.assertEqual(balance.diferencia, Decimal("13.00"))
        self.assertFalse(balance.balanceado)

    def test_balanceado_y_fecha_de_corte(self):
        self.registrar("1101", [linea(debe="113.00")])
        self.registrar("5101", [linea(haber="100.00")])
        self.registrar("2103", [
            linea(haber="13.00", fecha=datetime.date(2026, 11, 20))
        ])

        antes = self.servicio.balance_comprobacion(self.contador, FECHA)
        despues = self.servicio.balance_comprobacion(
            self.contador, datetime.date(2026, 11, 30)
        )

        self.assertEqual(len(antes.filas), 2)
        self.assertTrue(despues.balanceado)
        self.assertEqual(despues.filas[1].haber, Decimal("13.00"))

    def test_sin_movimientos_no_hay_filas(self):
        balance = self.servicio.balance_comprobacion(self.contador, FECHA)
        self.assertEqual(balance.filas, ())
        self.assertTrue(balance.balanceado)


class ExportarBalanceTest(LibroMayorTestCase):
    def test_pdf_con_las_cuentas_con_movimientos_y_totales(self):
        self.servicio = LibroMayorService(
            self.repositorio, self.bitacora, ConfiguracionLibroMayor(),
            exportador_balance=ExportadorBalancePDF(comprimir=False),
        )
        self.registrar("1101", [linea(debe="1250.00")])
        self.registrar("5101", [linea(haber="1000.00")])

        archivo = self.servicio.exportar_balance(self.contador, FECHA)

        self.assertTrue(archivo.contenido.startswith(b"%PDF"))
        self.assertEqual(archivo.nombre, "balance_comprobacion_20261103.pdf")
        for texto in (b"Balance de Comprobaci", b"Al 03/11/2026",
                      b"1101", b"5101", b"$1,250.00", b"$1,000.00",
                      b"Totales", b"$250.00"):
            self.assertIn(texto, archivo.contenido)
        self.assertNotIn(b"2103", archivo.contenido)
