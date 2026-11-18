"""Pruebas del subsistema de costos (órdenes de trabajo).

Cubren los valores exactos exigidos: tasas por proceso, ajustes de
diferencia, reparto de fondos con ajuste de centavos, costo por hora
pagada, idempotencia, período/orden cerrados, capitalización por fecha,
cortes provisionales/reversión y depreciación de equipos.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.test import TestCase

from catalogo.models import Cuenta
from costos import calculos
from costos.exceptions import (
    FondoYaDistribuidoError,
    OrdenCerradaError,
    PeriodoNoAbiertoError,
    SalarioNoVigenteError,
)
from costos.models import (
    CargoOrden,
    CostoProceso,
    CorteCostos,
    Equipo,
    FondoCompartido,
    MapeoCuenta,
    OrdenTrabajo,
    Proceso,
    RegistroHora,
    SalarioReferencia,
    UsoEquipo,
)
from costos.repositories import CostosRepository
from costos.services import CalculoService, OrdenService
from libro_mayor.models import EstadoPeriodo, PeriodoContable
from usuarios.models import Usuario
from usuarios.roles import Rol

D = Decimal
FECHA = date(2026, 6, 15)


class BaseCostos(TestCase):
    def setUp(self):
        self.actor = Usuario.objects.create(
            username="contador", nombre_completo="Contador",
            rol=Rol.CONTADOR_GENERAL, activo=True,
        )
        self.repo = CostosRepository()
        self.ordenes = OrdenService(self.repo, None, transaction.atomic)
        self.calculo = CalculoService(self.repo, None, transaction.atomic)
        self.periodo = PeriodoContable.objects.create(
            nombre="Junio 2026", fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 6, 30), estado=EstadoPeriodo.ABIERTO,
        )
        self.procesos = {
            p.nombre: p for p in Proceso.objects.all()
        }
        # Asegura los 4 procesos semilla por si el test DB no los tiene.
        for nombre in ("Programación", "Arte y animación", "Audio",
                       "QA y accesibilidad"):
            if nombre not in self.procesos:
                self.procesos[nombre] = self.repo.crear_proceso(
                    nombre=nombre,
                )

    def orden(self, nombre="Juego A", cap=date(2026, 1, 1)):
        return self.ordenes.crear_orden(
            self.actor, nombre_juego=nombre, capitalizable_desde=cap,
        )

    def hora(self, orden, proceso=None, horas="1", fecha=FECHA, rol="Dev"):
        return self.repo.crear_hora(
            orden=orden, proceso=proceso, rol=rol, horas=D(horas),
            fecha=fecha,
        )

    def costo_proceso(self, proceso, costo, horas_base,
                      tasa_presupuestada=None):
        return self.repo.crear_costo_proceso(
            proceso=proceso, periodo=self.periodo, costo=D(costo),
            horas_base=D(horas_base), tasa_presupuestada=tasa_presupuestada,
        )

    def cargo(self, orden, monto="100", fecha=FECHA, afecta=True,
              origen=CargoOrden.ORIGEN_DIRECTO, cuenta=None):
        if cuenta is None and afecta:
            cuenta = Cuenta.objects.get(codigo="4103")
        return self.repo.crear_cargo(
            orden=orden, origen=origen, afecta_mayor=afecta,
            monto=D(monto), fecha=fecha, descripcion="Cargo de prueba",
            cuenta=cuenta, usuario=self.actor,
        )


class CalculosPurosTests(TestCase):
    def test_horas_mensuales_y_costo_hora(self):
        horas_mes = calculos.horas_mensuales(44, 52)
        self.assertEqual(horas_mes.quantize(D("0.0001")), D("190.6667"))
        costo = calculos.costo_hora_pagada(1200, D("0.246"), horas_mes)
        self.assertEqual(costo.quantize(D("0.0001")), D("7.8420"))

    def test_repartir_conserva_total(self):
        cuotas = calculos.repartir(D("10000"),
                                   [D("500"), D("300"), D("200"), D("100")])
        self.assertEqual(cuotas, [
            D("4545.45"), D("2727.27"), D("1818.18"), D("909.10"),
        ])
        self.assertEqual(sum(cuotas), D("10000.00"))

    def test_tasa_y_cuota_depreciacion(self):
        self.assertEqual(calculos.tasa_proceso(60000, 1000), D("60"))
        self.assertEqual(calculos.tasa_proceso(30000, 600), D("50"))
        self.assertEqual(calculos.tasa_proceso(12000, 200), D("60"))
        self.assertEqual(
            calculos.cuota_depreciacion(12000, 0, 12), D("1000")
        )


class TasasProcesoTests(BaseCostos):
    def _escenario(self):
        prog = self.procesos["Programación"]
        arte = self.procesos["Arte y animación"]
        audio = self.procesos["Audio"]
        self.costo_proceso(prog, 60000, 1000)
        self.costo_proceso(arte, 30000, 600)
        self.costo_proceso(audio, 12000, 200)
        a = self.orden("Juego A")
        b = self.orden("Juego B")
        for orden, hs in ((a, (700, 400, 150)), (b, (300, 200, 50))):
            for proceso, horas in zip((prog, arte, audio), hs):
                self.hora(orden, proceso=proceso, horas=str(horas))
        return a, b

    def test_tasas_exactas_sin_diferencia(self):
        a, b = self._escenario()
        self.calculo.aplicar_tasas(self.actor, self.periodo.pk)
        monto_a = sum(
            c.monto for c in CargoOrden.objects.filter(
                orden=a, origen=CargoOrden.ORIGEN_PROCESO
            )
        )
        monto_b = sum(
            c.monto for c in CargoOrden.objects.filter(
                orden=b, origen=CargoOrden.ORIGEN_PROCESO
            )
        )
        self.assertEqual(monto_a, D("71000.00"))
        self.assertEqual(monto_b, D("31000.00"))
        self.assertEqual(monto_a + monto_b, D("102000.00"))

    def test_subaplicacion_repartida_por_horas(self):
        prog = self.procesos["Programación"]
        arte = self.procesos["Arte y animación"]
        self.costo_proceso(prog, 60000, 1000)
        # Arte: costo real 33,000 con tasa presupuestada 50 (30,000 base).
        self.costo_proceso(arte, 33000, 600,
                           tasa_presupuestada=D("50"))
        a = self.orden("Juego A")
        b = self.orden("Juego B")
        self.hora(a, proceso=prog, horas="700")
        self.hora(b, proceso=prog, horas="300")
        self.hora(a, proceso=arte, horas="400")
        self.hora(b, proceso=arte, horas="200")
        self.calculo.aplicar_tasas(
            self.actor, self.periodo.pk, usar_presupuestada=True
        )
        ajustes = {
            c.orden_id: c.monto for c in CargoOrden.objects.filter(
                origen=CargoOrden.ORIGEN_AJUSTE, proceso=arte,
            )
        }
        self.assertEqual(ajustes[a.pk], D("2000.00"))
        self.assertEqual(ajustes[b.pk], D("1000.00"))

    def test_aplicar_dos_veces_no_duplica(self):
        a, _ = self._escenario()
        self.calculo.aplicar_tasas(self.actor, self.periodo.pk)
        total = CargoOrden.objects.count()
        self.calculo.aplicar_tasas(self.actor, self.periodo.pk)
        self.assertEqual(CargoOrden.objects.count(), total)


class ManoObraTests(BaseCostos):
    def test_registrar_hora_genera_cargo_4101(self):
        SalarioReferencia.objects.create(
            rol="Dev", salario_bruto=D("1200"), vigente_desde=date(2020, 1, 1),
        )
        orden = self.orden()
        hora, cargo = self.ordenes.registrar_hora(
            self.actor, orden.pk, rol="Dev", horas=D("10"), fecha=FECHA,
        )
        self.assertEqual(cargo.cuenta.codigo, "4101")
        # 10 h × 7.8420… = 78.42
        self.assertEqual(cargo.monto, D("78.42"))
        self.assertEqual(cargo.clave_idempotencia, f"hora-{hora.pk}")

    def test_sin_salario_vigente_rechaza(self):
        orden = self.orden()
        with self.assertRaises(SalarioNoVigenteError):
            self.ordenes.registrar_hora(
                self.actor, orden.pk, rol="SinRol", horas=D("5"),
                fecha=FECHA,
            )
        self.assertEqual(RegistroHora.objects.count(), 0)


class FondoTests(BaseCostos):
    def test_reparto_10000_con_ajuste_de_centavos(self):
        horas = {"A": "500", "B": "300", "C": "200", "D": "100"}
        ordenes = {n: self.orden(f"Juego {n}") for n in horas}
        for n, h in horas.items():
            self.hora(ordenes[n], horas=h)
        fondo = self.calculo.crear_fondo(
            self.actor, nombre="Voces", monto=D("10000"), fecha=FECHA,
        )
        self.calculo.distribuir_fondo(self.actor, fondo.pk)
        montos = {
            c.orden.juego.nombre: c.monto
            for c in CargoOrden.objects.filter(fondo=fondo)
        }
        self.assertEqual(montos["Juego A"], D("4545.45"))
        self.assertEqual(montos["Juego B"], D("2727.27"))
        self.assertEqual(montos["Juego C"], D("1818.18"))
        self.assertEqual(montos["Juego D"], D("909.10"))
        self.assertEqual(sum(montos.values()), D("10000.00"))
        # Los cargos del fondo no afectan el mayor.
        self.assertTrue(all(
            not c.afecta_mayor and c.cuenta_id is None
            for c in CargoOrden.objects.filter(fondo=fondo)
        ))

    def test_fondo_ya_distribuido_no_reparte(self):
        orden = self.orden()
        self.hora(orden, horas="10")
        fondo = self.calculo.crear_fondo(
            self.actor, nombre="Música", monto=D("500"), fecha=FECHA,
        )
        self.calculo.distribuir_fondo(self.actor, fondo.pk)
        with self.assertRaises(FondoYaDistribuidoError):
            self.calculo.distribuir_fondo(self.actor, fondo.pk)


class CapitalizacionTests(BaseCostos):
    def test_cargos_anteriores_a_fecha_quedan_como_gasto(self):
        orden = self.orden(cap=date(2026, 6, 1))
        self.cargo(orden, monto="100", fecha=date(2026, 5, 15))
        self.cargo(orden, monto="200", fecha=date(2026, 6, 15))
        saldos = self.ordenes.saldos_orden(orden)
        self.assertEqual(saldos["en_41"], D("200.00"))
        self.assertEqual(saldos["gasto_periodo"], D("100.00"))

    def test_sin_fecha_capitalizable_nada_capitaliza(self):
        orden = self.orden(cap=None)
        self.cargo(orden, monto="100")
        saldos = self.ordenes.saldos_orden(orden)
        self.assertEqual(saldos["costo_contable"], D("0.00"))
        self.assertEqual(saldos["gasto_periodo"], D("100.00"))

    def test_afecta_mayor_false_no_genera_cuenta_ni_capitaliza(self):
        orden = self.orden()
        cargo = self.cargo(orden, monto="50", afecta=False)
        self.assertIsNone(cargo.cuenta_id)
        saldos = self.ordenes.saldos_orden(orden)
        self.assertEqual(saldos["costo_contable"], D("0.00"))
        self.assertEqual(saldos["costo_gestion"], D("50.00"))


class CorteTests(BaseCostos):
    def test_corte_provisional_y_reversion(self):
        orden = self.orden()
        self.cargo(orden, monto="300", cuenta=Cuenta.objects.get(
            codigo="4101"))
        self.cargo(orden, monto="200", cuenta=Cuenta.objects.get(
            codigo="4103"))
        corte = self.calculo.crear_corte(
            self.actor, periodo_id=self.periodo.pk,
            tipo=CorteCostos.TIPO_PROVISIONAL, motivo="Corte de junio",
        )
        # La serie 41 queda en cero para la orden; el mayor sigue abierto.
        saldos = self.ordenes.saldos_orden(orden)
        self.assertEqual(saldos["en_41"], D("0.00"))
        self.assertEqual(saldos["en_corte"], D("500.00"))
        self.assertEqual(self.periodo.estado, EstadoPeriodo.ABIERTO)
        self.assertEqual(corte.detalles.count(), 2)
        # Reversión: los saldos vuelven a la 41.
        self.calculo.revertir_corte(self.actor, corte.pk)
        saldos = self.ordenes.saldos_orden(orden)
        self.assertEqual(saldos["en_41"], D("500.00"))
        self.assertEqual(saldos["en_corte"], D("0.00"))

    def test_corte_definitivo_traslada_sin_revertir(self):
        orden = self.orden()
        self.cargo(orden, monto="300")
        corte = self.calculo.crear_corte(
            self.actor, periodo_id=self.periodo.pk,
            tipo=CorteCostos.TIPO_DEFINITIVO, motivo="Cierre de junio",
        )
        saldos = self.ordenes.saldos_orden(orden)
        self.assertEqual(saldos["intangible"], D("300.00"))
        self.assertEqual(saldos["en_41"], D("0.00"))
        with self.assertRaises(Exception):
            self.calculo.revertir_corte(self.actor, corte.pk)

    def test_orden_cerrada_rechaza_cargos(self):
        orden = self.orden()
        self.ordenes.cerrar_orden(
            self.actor, orden.pk, confirmacion="CONFIRMAR",
            motivo="Lanzamiento",
        )
        with self.assertRaises(OrdenCerradaError):
            self.ordenes.registrar_cargo(
                self.actor, orden.pk, origen=CargoOrden.ORIGEN_DIRECTO,
                afecta_mayor=True, monto=D("10"), fecha=FECHA,
                descripcion="Cargo tardío", concepto_cuenta="indirecto",
            )


class ReglasPeriodoTests(BaseCostos):
    def test_periodo_cerrado_rechaza_cargo(self):
        cerrado = PeriodoContable.objects.create(
            nombre="Cerrado", fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31),
            estado=EstadoPeriodo.CIERRE_PROVISIONAL,
        )
        orden = self.orden()
        with self.assertRaises(PeriodoNoAbiertoError):
            self.ordenes.registrar_cargo(
                self.actor, orden.pk, origen=CargoOrden.ORIGEN_DIRECTO,
                afecta_mayor=True, monto=D("10"),
                fecha=date(2026, 7, 10), descripcion="x",
            )

    def test_periodo_cerrado_rechaza_horas(self):
        PeriodoContable.objects.create(
            nombre="Julio cerrado", fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31),
            estado=EstadoPeriodo.CIERRE_PROVISIONAL,
        )
        orden = self.orden()
        SalarioReferencia.objects.create(
            rol="Dev", salario_bruto=D("1200"), vigente_desde=date(2020, 1, 1),
        )
        with self.assertRaises(PeriodoNoAbiertoError):
            self.ordenes.registrar_hora(
                self.actor, orden.pk, rol="Dev", horas=D("1"),
                fecha=date(2026, 7, 10),
            )


class DepreciacionTests(BaseCostos):
    def _equipo(self, tipo, orden=None, costo="12000", residual="0",
                vida=12, horas_mes="200"):
        return self.repo.crear_equipo(
            nombre=f"EQ-{tipo}", costo=D(costo), valor_residual=D(residual),
            vida_util_meses=vida, tipo_uso=tipo, orden=orden,
            horas_mes=D(horas_mes), fecha_adquisicion=date(2026, 1, 1),
        )

    def test_exclusivo_carga_cuota_completa(self):
        orden = self.orden()
        equipo = self._equipo("EXCLUSIVO", orden=orden)
        self.calculo.generar_depreciacion(self.actor, anio=2026, mes=6)
        cargo = CargoOrden.objects.get(equipo=equipo)
        self.assertEqual(cargo.monto, D("1000.00"))
        self.assertEqual(cargo.origen, CargoOrden.ORIGEN_DEPRECIACION)

    def test_compartido_por_tasa_hora_maquina(self):
        # cuota 1000/mes, 200 h/mes → 5.00/h; A 100 h, B 50 h.
        a, b = self.orden("A"), self.orden("B")
        equipo = self._equipo("COMPARTIDO")
        UsoEquipo.objects.create(
            equipo=equipo, orden=a, fecha=date(2026, 6, 10), horas=D("100"))
        UsoEquipo.objects.create(
            equipo=equipo, orden=b, fecha=date(2026, 6, 10), horas=D("50"))
        self.calculo.generar_depreciacion(self.actor, anio=2026, mes=6)
        montos = {
            c.orden_id: c.monto
            for c in CargoOrden.objects.filter(equipo=equipo)
        }
        self.assertEqual(montos[a.pk], D("500.00"))
        self.assertEqual(montos[b.pk], D("250.00"))

    def test_admin_y_ocioso_no_generan_cargos(self):
        self._equipo("ADMINISTRACION")
        self._equipo("OCIOSO")
        self.calculo.generar_depreciacion(self.actor, anio=2026, mes=6)
        self.assertEqual(CargoOrden.objects.count(), 0)

    def test_depreciacion_idempotente(self):
        orden = self.orden()
        self._equipo("EXCLUSIVO", orden=orden)
        self.calculo.generar_depreciacion(self.actor, anio=2026, mes=6)
        total = CargoOrden.objects.count()
        self.calculo.generar_depreciacion(self.actor, anio=2026, mes=6)
        self.assertEqual(CargoOrden.objects.count(), total)
