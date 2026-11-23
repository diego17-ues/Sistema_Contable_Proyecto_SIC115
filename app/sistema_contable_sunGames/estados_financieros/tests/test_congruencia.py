"""Congruencia de los estados financieros con costos, cobros y cierre.

Cubre las pruebas pedidas: mano de obra 176 h, costo directo con Bancos,
depreciación y amortización de desarrollo a 4103 sin duplicar, cobro
conciliado, cierre con serie 41 en cero y costo de ventas igual a la
cuota de amortización, y estados/balanza que cuadran.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import mock

from django.db.models import Sum
from django.test import SimpleTestCase, TestCase

from costos import calculos
from costos.composition import (
    crear_orden_service,
    crear_reclasificacion_service,
    crear_registro_service,
)
from costos.models import (
    AmortizacionVideojuego,
    ConfiguracionCuentaCosto,
    Elemento,
    ParametroAmortizacion,
    Proceso,
)
from estados_financieros import calculo
from estados_financieros.composition import crear_cierre_service
from estados_financieros.models import EstadoFinancieroEmitido, TipoEstado
from estados_financieros.tests.fakes import cuenta_con_saldo, periodo
from libro_mayor.models import Movimiento, PeriodoContable
from usuarios.models import Usuario
from usuarios.roles import Rol
from ventas.composition import crear_ventas_service

D = Decimal
NOVIEMBRE = (date(2026, 11, 1), date(2026, 11, 30))
SERIE_41 = ("4101", "4102", "4103")


def saldo(*codigos, hasta=None):
    filtro = {"cuenta__codigo__in": codigos}
    if hasta:
        filtro["fecha__lte"] = hasta
    return (Movimiento.objects.filter(**filtro)
            .aggregate(t=Sum("importe"))["t"] or D("0"))


class CalculoCongruenteTests(SimpleTestCase):
    def test_serie_41_no_es_gasto_y_el_balance_cuadra(self):
        datos = {"1101": "500", "4101": "800", "4104": "200",
                 "2101": "-800", "5101": "-700"}
        saldos = [cuenta_con_saldo(c, s) for c, s in sorted(datos.items())]
        resultados = calculo.estado_resultados(periodo(), saldos)
        codigos = {f["codigo"] for f in resultados["filas"]}
        self.assertNotIn("4101", codigos)
        utilidad = [f for f in resultados["filas"]
                    if f["clase"] == "resultado"][0]
        self.assertEqual(utilidad["importe"], "500.00")
        balance = calculo.balance_general(periodo(), saldos)
        self.assertTrue(balance["cuadra"], balance["diferencia"])
        self.assertIn("4101", {f["codigo"] for f in balance["filas"]})

    def test_cuota_por_modalidad(self):
        base = D("4800.00")
        nov = dict(base=base, acumulado=0, vida_util_meses=48,
                   desde=date(2026, 11, 1), hasta=date(2026, 11, 30))
        self.assertEqual(calculos.cuota_amortizacion(modalidad="MENSUAL",
                                                     **nov), D("100.00"))
        self.assertEqual(calculos.cuota_amortizacion(modalidad="DIARIA",
                                                     **nov), D("98.63"))
        self.assertEqual(calculos.cuota_amortizacion(modalidad="ANUAL",
                                                     **nov), D("0"))
        anio = {**nov, "desde": date(2026, 1, 1),
                "hasta": date(2026, 12, 31)}
        self.assertEqual(calculos.cuota_amortizacion(modalidad="ANUAL",
                                                     **anio), D("1200.00"))
        self.assertEqual(calculos.cuota_amortizacion(
            modalidad="MENSUAL", **{**nov, "acumulado": "4750"}), D("50.00"))


class CongruenciaIntegracionTests(TestCase):
    def setUp(self):
        self.general = Usuario.objects.create(
            username="general", nombre_completo="General",
            rol=Rol.CONTADOR_GENERAL, activo=True,
        )
        self.costos = Usuario.objects.create(
            username="costos", nombre_completo="Costos",
            rol=Rol.CONTADOR_COSTOS, activo=True,
        )
        self.registros = crear_registro_service()
        self.ordenes = crear_orden_service()
        self.orden = self.ordenes.crear_orden(
            self.costos, nombre_juego="Neo Drift",
            fecha_inicio=date(2026, 11, 1),
        )
        self.proceso = Proceso.objects.get(nombre="Programación")
        self.config = {
            c.elemento: c for c in ConfiguracionCuentaCosto.objects.all()
        }
        ParametroAmortizacion.objects.update(modalidad="MENSUAL",
                                             vida_util_meses=48)

    def contrapartida(self, elemento, codigo):
        return self.config[elemento].contrapartidas.get(codigo=codigo).pk

    def costo(self, elemento, importe, codigo, descripcion="Costo"):
        return self.registros.registrar_costo(
            self.costos, elemento=elemento, orden_id=self.orden.pk,
            fecha=date(2026, 11, 12), proceso_id=None,
            descripcion=descripcion, importe=importe,
            contrapartida_id=self.contrapartida(elemento, codigo),
            clave=uuid.uuid4().hex,
        )

    def movimientos(self, registro):
        asiento = registro.asientos.get()
        return {m.cuenta.codigo: m.importe
                for m in asiento.transaccion.movimientos.all()}

    def mano_obra(self):
        return self.registros.registrar_mano_obra(
            self.costos, orden_id=self.orden.pk, fecha=date(2026, 11, 10),
            proceso_id=self.proceso.pk, horas="176", costo_hora="5.00",
            contrapartida_id=None, clave=uuid.uuid4().hex,
        )

    def test_1_mano_de_obra_176_horas(self):
        registro = self.mano_obra()
        lineas = self.movimientos(registro)
        self.assertEqual(lineas["4101"], registro.importe)
        self.assertLess(lineas["2106"], 0)
        self.assertEqual(sum(lineas.values()), 0)
        self.assertEqual(saldo("4101"), registro.importe)
        self.assertGreaterEqual(registro.importe, D("880.00"))

    def test_2_costo_directo_contra_bancos(self):
        registro = self.costo(Elemento.DIRECTO, "1200.00", "1103")
        self.assertEqual(self.movimientos(registro),
                         {"4102": D("1200.00"), "1103": D("-1200.00")})

    def test_3_depreciacion_y_amortizacion_de_desarrollo_un_asiento(self):
        depreciacion = self.costo(Elemento.INDIRECTO, "100.00", "1203",
                                  "Depreciación equipo de desarrollo")
        licencia = self.costo(Elemento.INDIRECTO, "50.00", "1205",
                              "Amortización licencia del motor")
        self.assertEqual(self.movimientos(depreciacion),
                         {"4103": D("100.00"), "1203": D("-100.00")})
        self.assertEqual(self.movimientos(licencia),
                         {"4103": D("50.00"), "1205": D("-50.00")})
        self.assertEqual(saldo("4207", "4208"), 0)
        self.assertEqual(Movimiento.objects.filter(
            cuenta__codigo="1203").count(), 1)

    def vender_y_conciliar(self):
        ventas = crear_ventas_service()
        ventas.recibir(
            identificador="STM-C1", titulo="Neo Drift", tipo_producto="JUEGO",
            cantidad=2, precio_unitario=D("19.99"), moneda="USD", pais="SV",
            fecha_hora=datetime(2026, 11, 3, 15, tzinfo=timezone.utc),
            comision=D("12.00"),
        )
        resumen = ventas.conciliar(self.general, *NOVIEMBRE)
        ventas.conciliar(self.general, *NOVIEMBRE)
        return resumen

    def test_4_cobro_conciliado_baja_cxc_y_sube_bancos(self):
        resumen = self.vender_y_conciliar()
        self.assertEqual(resumen.conciliadas, 1)
        self.assertEqual(saldo("1104"), D("0.00"))
        self.assertEqual(saldo("1103"), D("27.98"))
        self.assertEqual(Movimiento.objects.filter(
            cuenta__codigo="1103").count(), 1)

    def test_5_y_6_cierre_serie_41_cero_y_costo_ventas_igual_cuota(self):
        self.mano_obra()
        self.costo(Elemento.DIRECTO, "1200.00", "1103")
        self.costo(Elemento.INDIRECTO, "100.00", "1203")
        self.vender_y_conciliar()
        base = saldo(*SERIE_41)
        with mock.patch("costos.services.timezone.localdate",
                        return_value=date(2026, 11, 15)):
            self.ordenes.finalizar(self.costos, self.orden.pk)
        crear_cierre_service().cerrar_rango(
            self.general, *NOVIEMBRE, confirmacion="CONFIRMAR",
            motivo="Cierre de noviembre",
        )
        cuota = (base / 48).quantize(D("0.01"))
        self.assertEqual(saldo(*SERIE_41), 0)
        self.assertEqual(saldo("1107"), base)
        self.assertEqual(saldo("4104"), cuota)
        self.assertEqual(saldo("1108"), -cuota)
        self.assertEqual(AmortizacionVideojuego.objects.get().importe, cuota)

        cierre = PeriodoContable.objects.get(fecha_inicio=NOVIEMBRE[0],
                                             fecha_fin=NOVIEMBRE[1])
        emitidos = {e.tipo: e.datos for e in
                    EstadoFinancieroEmitido.objects.filter(periodo=cierre)}
        resultados = emitidos[TipoEstado.ESTADO_RESULTADOS]["filas"]
        costo_ventas = [f for f in resultados
                        if f["texto"] == "Total costo de ventas"][0]
        self.assertEqual(D(costo_ventas["importe"]), -cuota)
        codigos = {f["codigo"] for f in resultados}
        self.assertTrue(codigos.isdisjoint(SERIE_41))
        nota = [f for f in resultados if f["codigo"] == "1108"][0]
        self.assertEqual(D(nota["importe"]), cuota)
        utilidad = [f for f in resultados if f["clase"] == "resultado"][0]
        ingresos = D("39.98") - D("12.00")
        self.assertEqual(D(utilidad["importe"]), ingresos - cuota)
        self.assertTrue(emitidos[TipoEstado.BALANCE_GENERAL]["cuadra"])
        self.assertEqual(saldo(*Movimiento.objects.values_list(
            "cuenta__codigo", flat=True).distinct()), 0)

        # Otro período que se solapa (ejercicio anual): no repite noviembre.
        ejercicio = PeriodoContable.objects.get(nombre="Ejercicio 2026")
        crear_reclasificacion_service().amortizar_periodo(self.general,
                                                          ejercicio)
        diciembre = AmortizacionVideojuego.objects.get(periodo=ejercicio)
        self.assertEqual(diciembre.desde, date(2026, 12, 1))
        self.assertEqual(diciembre.importe, cuota)
        self.assertEqual(saldo("4104"), -saldo("1108"))
