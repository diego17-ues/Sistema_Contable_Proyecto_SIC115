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
    ConfiguracionNoEncontradaError,
    CuentaNoValidaError,
    DatosInsuficientesError,
    OrdenDuplicadaError,
    PeriodoNoAbiertoError,
    RegistroYaAnuladoError,
)
from costos.forms import OrdenForm
from costos.models import (
    AsientoCosto,
    ConfiguracionCuentaCosto,
    Elemento,
    FuenteIndirecta,
    OrdenTrabajo,
    Proceso,
    RegistroCosto,
)
from costos.repositories import CostosRepository
from costos.services import (
    AplicacionIndirectosService,
    CatalogoCostosService,
    OrdenService,
    RegistroCostoService,
)
from libro_mayor.models import (
    EstadoPeriodo,
    Movimiento,
    PeriodoContable,
    TipoMovimiento,
)
from libro_mayor.repositories import TransaccionRepository
from usuarios.exceptions import RolNoAutorizadoError
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

    def test_distribucion_por_horas_y_ajuste_de_centavos(self):
        self.assertEqual(
            calculos.distribuir_por_horas(
                D("1000.00"), {1: D("120"), 2: D("80")}
            ),
            {1: D("600.00"), 2: D("400.00")},
        )
        self.assertEqual(
            calculos.distribuir_por_horas(
                D("600.00"), {1: D("160"), 2: D("140")}
            ),
            {1: D("320.00"), 2: D("280.00")},
        )
        reparto = calculos.distribuir_por_horas(
            D("10000.00"), {
                1: D("500"), 2: D("300"), 3: D("200"), 4: D("100"),
            }
        )
        self.assertEqual(
            list(reparto.values()),
            [D("4545.45"), D("2727.27"), D("1818.18"), D("909.10")],
        )
        self.assertEqual(sum(reparto.values()), D("10000.00"))

    def test_acumulacion_reclasificacion_y_contrarias(self):
        self.assertEqual(
            calculos.linea_acumulacion("4101", D("83.33")),
            [("4101", D("83.33"))],
        )
        lineas = calculos.lineas_reclasificacion(
            "origen", "destino", D("83.33")
        )
        self.assertEqual(
            lineas, [("destino", D("83.33")), ("origen", D("-83.33"))]
        )
        self.assertTrue(calculos.cuadra(lineas))
        self.assertEqual(
            calculos.lineas_contrarias(lineas),
            [("destino", D("-83.33")), ("origen", D("83.33"))],
        )

    def test_comparacion_estimado_real_y_porcentaje(self):
        evaluacion = calculos.comparar_estimado_real(
            D("100.00"), D("125.00")
        )
        self.assertEqual(evaluacion["variacion"], D("25.00"))
        self.assertEqual(evaluacion["porcentaje"], D("25.00"))
        self.assertEqual(evaluacion["estado"], "POR_ENCIMA")
        self.assertFalse(evaluacion["viable"])

        evaluacion = calculos.comparar_estimado_real(
            D("100.00"), D("75.00")
        )
        self.assertEqual(evaluacion["variacion"], D("-25.00"))
        self.assertEqual(evaluacion["porcentaje"], D("-25.00"))
        self.assertEqual(evaluacion["estado"], "POR_DEBAJO")
        self.assertTrue(evaluacion["viable"])

        evaluacion = calculos.comparar_estimado_real(
            D("100.00"), D("100.00")
        )
        self.assertEqual(evaluacion["variacion"], D("0.00"))
        self.assertEqual(evaluacion["estado"], "COINCIDE")
        self.assertTrue(evaluacion["viable"])

    def test_comparacion_no_divide_entre_estimacion_cero(self):
        evaluacion = calculos.comparar_estimado_real(
            D("0.00"), D("12.50")
        )
        self.assertIsNone(evaluacion["porcentaje"])
        self.assertEqual(evaluacion["estado"], "POR_ENCIMA")


class OrdenFormTests(SimpleTestCase):
    def test_estimacion_seleccionada_completa_el_juego(self):
        version = SimpleNamespace(
            pk=12,
            juego=SimpleNamespace(nombre="Neo Drift"),
            numero=3,
            get_estado_display=lambda: "Vigente",
        )
        form = OrdenForm(
            data={
                "nombre_juego": "",
                "estimacion": "12",
                "fecha_inicio": "2026-06-15",
            },
            estimaciones=[version],
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["nombre_juego"], "Neo Drift")

    def test_sin_estimacion_requiere_nombre_del_juego(self):
        form = OrdenForm(data={
            "nombre_juego": "",
            "estimacion": "",
            "fecha_inicio": "2026-06-15",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("nombre_juego", form.errors)


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
        config = SimpleNamespace(cuenta_costo=self.debe)
        self.repo = _RepoMemoria(config)
        self.mayor = _MayorMemoria()
        self.actor = SimpleNamespace(activo=True, rol=Rol.CONTADOR_COSTOS)
        self.servicio = RegistroCostoService(self.repo, self.mayor, None,
                                             nullcontext)

    def _mano_obra(self, clave_="k1"):
        return self.servicio.registrar_mano_obra(
            self.actor, orden_id=1, fecha=FECHA, proceso_id=7, horas="40",
            costo_hora="20.00", clave=clave_,
        )

    def test_asiento_acumula_en_cuenta_de_costo(self):
        registro = self._mano_obra()
        self.assertEqual(registro.importe, D("800.00"))
        importes = [m["importe"] for m in self.mayor.movimientos]
        self.assertEqual(importes, [D("800.00")])
        self.assertTrue(all("OT-1" in m["referencia"]
                            for m in self.mayor.movimientos))
        self.assertEqual(self.repo.asientos[0]["clave_idempotencia"], "k1")

    def test_misma_clave_no_duplica(self):
        primero = self._mano_obra()
        segundo = self._mano_obra()
        self.assertIs(primero, segundo)
        self.assertEqual(len(self.mayor.movimientos), 1)

    def test_periodo_cerrado_rechaza(self):
        self.mayor.cerrado = True
        with self.assertRaises(PeriodoNoAbiertoError):
            self._mano_obra()
        self.assertEqual(self.mayor.movimientos, [])

    def test_sin_configuracion_bloquea(self):
        self.repo.config = None
        with self.assertRaises(ConfiguracionNoEncontradaError):
            self._mano_obra()

    def test_importe_redondeado_a_cero_rechaza(self):
        with self.assertRaises(DatosInsuficientesError):
            self.servicio.registrar_mano_obra(
                self.actor, orden_id=1, fecha=FECHA, proceso_id=7,
                horas="0.01", costo_hora="0.01", clave="k3",
            )
        self.assertEqual(self.mayor.movimientos, [])

    def test_horas_en_cero_rechaza(self):
        with self.assertRaises(DatosInsuficientesError):
            self.servicio.registrar_mano_obra(
                self.actor, orden_id=1, fecha=FECHA, proceso_id=7,
                horas="0", costo_hora="20", clave="k2",
            )


# ---------------------------------------------------------- integración

class BaseCostos(TestCase):
    def setUp(self):
        self.actor = Usuario.objects.create(
            username="contador", nombre_completo="Contador",
            rol=Rol.CONTADOR_COSTOS, activo=True,
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
            costo_hora=costo, clave=extra.get("clave") or clave(),
        )

    def costo(self, elemento, importe, proceso=None, **extra):
        return self.servicio.registrar_costo(
            self.actor, elemento=elemento, orden_id=self.orden.pk,
            fecha=extra.get("fecha", FECHA),
            proceso_id=proceso.pk if proceso else None,
            descripcion=extra.get("descripcion", "Servicio"),
            importe=importe, clave=extra.get("clave") or clave(),
        )

    def movimientos(self, registro, tipo=AsientoCosto.TIPO_REGISTRO):
        asiento = registro.asientos.get(tipo=tipo)
        return {m.cuenta.codigo: m.importe for m in
                Movimiento.objects.filter(transaccion=asiento.transaccion)}

    def total_vigente(self):
        return RegistroCosto.objects.filter(
            orden=self.orden, estado=RegistroCosto.ESTADO_VIGENTE,
        ).aggregate(t=Sum("importe"))["t"] or D("0")


class RegistroElementosTests(BaseCostos):
    def test_administrador_puede_crear_orden_y_registrar_costos(self):
        admin = Usuario.objects.create(
            username="admin-costos", nombre_completo="Administrador",
            rol=Rol.ADMINISTRADOR, activo=True,
        )
        orden = self.ordenes.crear_orden(
            admin, nombre_juego="Orden Administrador", fecha_inicio=FECHA,
        )

        registro = self.servicio.registrar_costo(
            admin, elemento=Elemento.DIRECTO, orden_id=orden.pk,
            fecha=FECHA, proceso_id=None, descripcion="Servicio de arte",
            importe="75.00", clave=clave(),
        )

        self.assertEqual(registro.orden_id, orden.pk)
        self.assertEqual(registro.importe, D("75.00"))

    def test_mano_obra_40_horas_por_20_es_800(self):
        registro = self.mano_obra()
        self.assertEqual(registro.importe, D("800.00"))
        self.assertEqual(self.movimientos(registro),
                         {"4101": D("800.00")})

    def test_costo_directo_1200(self):
        registro = self.costo(Elemento.DIRECTO, "1200.00")
        self.assertEqual(self.movimientos(registro),
                         {"4102": D("1200.00")})

    def test_costo_indirecto_83_33_acumula_solo_en_costo(self):
        registro = self.costo(Elemento.INDIRECTO, "83.33")
        self.assertEqual(self.movimientos(registro),
                         {"4103": D("83.33")})

    def test_total_de_los_tres_registros(self):
        self.mano_obra()
        self.costo(Elemento.DIRECTO, "1200.00")
        self.costo(Elemento.INDIRECTO, "83.33")
        self.assertEqual(self.total_vigente(), D("2083.33"))

    def test_asientos_acumulan_con_origen_y_clave(self):
        registros = [self.mano_obra(clave="mo-1"),
                     self.costo(Elemento.DIRECTO, "1200", clave="cd-1")]
        for registro in registros:
            asiento = registro.asientos.get()
            movimientos = Movimiento.objects.filter(
                transaccion=asiento.transaccion)
            self.assertEqual(len(movimientos), 1)
            self.assertTrue(all(m.importe > 0 for m in movimientos))
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
        self.assertEqual(Movimiento.objects.count(), 1)

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

    def test_sin_configuracion_el_elemento_queda_bloqueado(self):
        ConfiguracionCuentaCosto.objects.filter(
            elemento=Elemento.INDIRECTO).delete()
        with self.assertRaises(ConfiguracionNoEncontradaError):
            self.costo(Elemento.INDIRECTO, "10")

    def test_orden_duplicada_por_juego(self):
        with self.assertRaises(OrdenDuplicadaError):
            self.ordenes.crear_orden(self.actor, nombre_juego="neo drift",
                                     fecha_inicio=FECHA)


class AplicacionIndirectosTests(BaseCostos):
    def setUp(self):
        super().setUp()
        self.mayor = TransaccionRepository()
        self.catalogo = CatalogoCostosService(
            self.repo, None, transaction.atomic
        )
        self.aplicacion = AplicacionIndirectosService(
            self.repo, self.mayor, None, transaction.atomic
        )

    def crear_fuente(self, cuenta=None):
        return self.catalogo.crear_fuente_indirecta(
            self.actor, nombre="Servicios de desarrollo",
            tipo=FuenteIndirecta.Tipo.SERVICIO,
            cuenta=cuenta or self.cuenta("4205"),
            exclusiva_desarrollo=True,
        )

    def aportar_pool(self, importe, cuenta=None):
        transaccion = self.mayor.crear_transaccion(usuario=self.actor)
        cuenta = cuenta or self.cuenta("4205")
        self.mayor.crear_movimiento(
            transaccion=transaccion, cuenta=cuenta, fecha=FECHA,
            concepto="Servicio consumido", referencia="Gasto compartido",
            tipo=TipoMovimiento.DIARIO, importe=D(importe),
        )
        self.mayor.crear_movimiento(
            transaccion=transaccion, cuenta=self.cuenta("1103"),
            fecha=FECHA, concepto="Pago del servicio", referencia="Pago",
            tipo=TipoMovimiento.DIARIO, importe=-D(importe),
        )

    def agregar_orden_con_horas(self, nombre, horas, proceso=None):
        orden = self.ordenes.crear_orden(
            self.actor, nombre_juego=nombre, fecha_inicio=FECHA,
        )
        self.servicio.registrar_mano_obra(
            self.actor, orden_id=orden.pk, fecha=FECHA,
            proceso_id=(proceso or self.programacion).pk,
            horas=horas, costo_hora="1.00", clave=clave(),
        )
        return orden

    def test_pool_se_distribuye_por_horas_y_no_se_duplica(self):
        self.mano_obra(horas="120", costo="1.00")
        otra = self.agregar_orden_con_horas("Otro juego", "80")
        fuente = self.crear_fuente()
        self.aportar_pool("1000.00", fuente.cuenta_origen)

        vista = self.aplicacion.previsualizar(self.actor, self.periodo.pk)

        self.assertEqual(vista["total_pool"], D("1000.00"))
        self.assertEqual(vista["total_distribuido"], D("1000.00"))
        self.assertEqual(
            [linea["importe"] for linea in vista["distribucion"]],
            [D("600.00"), D("400.00")],
        )
        self.aplicacion.aplicar(self.actor, self.periodo.pk)
        registros = list(self.repo.registros_indirectos_periodo(self.periodo))
        self.assertEqual(len(registros), 2)
        por_orden = {r.orden_id: r.importe for r in registros}
        self.assertEqual(por_orden[self.orden.pk], D("600.00"))
        self.assertEqual(por_orden[otra.pk], D("400.00"))
        for registro in registros:
            self.assertEqual(
                self.movimientos(registro),
                {"4103": registro.importe,
                 fuente.cuenta_origen.codigo: -registro.importe},
            )

        self.aplicacion.aplicar(self.actor, self.periodo.pk)
        self.assertEqual(
            len(list(self.repo.registros_indirectos_periodo(self.periodo))), 2
        )

    def test_fuente_sin_horas_no_aplica_y_muestra_alerta(self):
        fuente = self.crear_fuente()
        self.aportar_pool("600.00", fuente.cuenta_origen)

        vista = self.aplicacion.aplicar(self.actor, self.periodo.pk)

        self.assertEqual(vista["distribucion"], [])
        self.assertTrue(any("ninguna orden abierta" in aviso
                            for aviso in vista["alertas"]))
        self.assertFalse(RegistroCosto.objects.filter(
            fuente_indirecta=fuente
        ).exists())

    def test_orden_cerrada_no_recibe_prorrateo(self):
        self.mano_obra(horas="40", costo="1.00")
        cerrada = self.agregar_orden_con_horas("Juego cerrado", "60")
        cerrada.estado = OrdenTrabajo.ESTADO_CERRADA
        cerrada.save()
        fuente = self.crear_fuente()
        self.aportar_pool("100.00", fuente.cuenta_origen)

        vista = self.aplicacion.previsualizar(self.actor, self.periodo.pk)

        self.assertEqual(len(vista["distribucion"]), 1)
        self.assertEqual(vista["distribucion"][0]["orden_id"], self.orden.pk)
        self.assertEqual(vista["distribucion"][0]["horas"], D("40.00"))

    def test_cuenta_excluida_no_se_distribuye(self):
        fuente = self.crear_fuente()
        self.catalogo.excluir_cuenta_indirecta(
            self.actor, cuenta=fuente.cuenta_origen,
            motivo="Cuenta compartida con administración",
        )
        self.mano_obra()
        self.aportar_pool("600.00", fuente.cuenta_origen)

        vista = self.aplicacion.previsualizar(self.actor, self.periodo.pk)

        self.assertEqual(vista["distribucion"], [])
        fuente.refresh_from_db()
        self.assertFalse(fuente.activa)

    def test_reversion_crea_contra_asiento_por_periodo(self):
        self.mano_obra()
        fuente = self.crear_fuente()
        self.aportar_pool("100.00", fuente.cuenta_origen)
        self.aplicacion.aplicar(self.actor, self.periodo.pk)
        registro = RegistroCosto.objects.get(fuente_indirecta=fuente)

        resultado = self.aplicacion.revertir(self.actor, self.periodo.pk)

        registro.refresh_from_db()
        self.assertEqual(registro.estado, RegistroCosto.ESTADO_ANULADO)
        self.assertTrue(resultado["puede_revertir"] is False)
        self.assertEqual(
            self.movimientos(registro, AsientoCosto.TIPO_ANULACION),
            {"4103": D("-100.00"),
             fuente.cuenta_origen.codigo: D("100.00")},
        )
        movimientos_antes = Movimiento.objects.count()
        self.aplicacion.revertir(self.actor, self.periodo.pk)
        self.assertEqual(Movimiento.objects.count(), movimientos_antes)

    def test_no_aplica_en_periodo_cerrado(self):
        self.mano_obra()
        fuente = self.crear_fuente()
        self.aportar_pool("100.00", fuente.cuenta_origen)
        self.periodo.estado = EstadoPeriodo.CIERRE_PROVISIONAL
        self.periodo.save()

        with self.assertRaises(PeriodoNoAbiertoError):
            self.aplicacion.aplicar(self.actor, self.periodo.pk)

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
        self.assertEqual(
            self.movimientos(directo, AsientoCosto.TIPO_ANULACION),
            {"4102": D("-1200.00")},
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
        catalogo.guardar_configuracion(
            self.actor, elemento=Elemento.MANO_OBRA,
            cuenta_costo=self.cuenta("4102"),
        )
        registro = self.mano_obra()
        self.assertEqual(self.movimientos(registro),
                         {"4102": D("800.00")})
        with self.assertRaises(CuentaNoValidaError):
            catalogo.guardar_configuracion(
                self.actor, elemento=Elemento.MANO_OBRA,
                cuenta_costo=None,
            )


class VistasCostosTests(BaseCostos):
    def setUp(self):
        super().setUp()
        self.actor.set_password("clave-segura-123")
        self.actor.save()
        self.client.force_login(self.actor)

    def test_admin_accede_a_costos_y_contador_general_no(self):
        general = Usuario.objects.create(
            username="general", nombre_completo="General",
            rol=Rol.CONTADOR_GENERAL, activo=True,
        )
        with self.assertRaises(RolNoAutorizadoError):
            self.ordenes.listar(general)
        self.client.force_login(general)
        self.assertEqual(
            self.client.get(reverse("costos_ordenes")).status_code, 403
        )

        admin = Usuario.objects.create(
            username="admin", nombre_completo="Administrador",
            rol=Rol.ADMINISTRADOR, activo=True,
        )
        self.assertEqual(len(self.ordenes.listar(admin)), 1)
        self.client.force_login(admin)
        for nombre in (
            "costos_ordenes", "costos_catalogos",
            "costos_indirectos_periodo", "costos_rendimiento",
            "costos_dashboard_api",
        ):
            with self.subTest(pantalla=nombre):
                self.assertEqual(
                    self.client.get(reverse(nombre)).status_code, 200
                )

    def test_dashboard_resume_ordenes_pendientes_y_finalizadas(self):
        self.orden.estado = OrdenTrabajo.ESTADO_CERRADA
        self.orden.save(update_fields=["estado"])

        respuesta = self.client.get(reverse("costos_dashboard_api"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["ordenesPendientes"], 0)
        self.assertEqual(respuesta.json()["ordenesFinalizadas"], 1)
        self.assertEqual(
            respuesta.json()["ultimaOrden"]["juego"], "Neo Drift"
        )
        self.assertEqual(
            respuesta.json()["ultimaOrdenRegistrada"]["estado"], "Cerrada"
        )
        self.assertEqual(
            respuesta.json()["ultimaOrdenRegistrada"]["id"], self.orden.pk
        )
        self.assertEqual(
            respuesta.json()["ordenesFinalizadasRecientes"][0]["id"],
            self.orden.pk,
        )

    def test_contador_general_solo_lee_el_resumen_de_costos(self):
        general = Usuario.objects.create(
            username="general", nombre_completo="General",
            rol=Rol.CONTADOR_GENERAL, activo=True,
        )
        self.client.force_login(general)

        respuesta = self.client.get(reverse("costos_dashboard_api"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["ordenesPendientes"], 1)
        self.assertEqual(respuesta.json()["ordenesFinalizadas"], 0)
        self.assertEqual(
            respuesta.json()["ultimaOrdenRegistrada"]["estado"], "Abierta"
        )

    def test_doble_envio_del_formulario_no_duplica(self):
        url = reverse("costos_registro_nuevo",
                      args=[self.orden.pk, "directo"])
        datos = {"fecha": "2026-06-15", "descripcion": "Licencia motor",
                 "importe": "1200.00", "clave": "form-1"}
        for _ in range(2):
            respuesta = self.client.post(url, datos)
            self.assertRedirects(
                respuesta, reverse("costos_orden", args=[self.orden.pk]))
        self.assertEqual(RegistroCosto.objects.count(), 1)
        self.assertEqual(Movimiento.objects.count(), 1)

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
        })
        self.assertContains(respuesta, "período contable")
        self.assertContains(respuesta, 'value="Luz"')
        self.assertEqual(RegistroCosto.objects.count(), 0)


class HojaCostosTests(BaseCostos):
    def setUp(self):
        super().setUp()
        self.ordenes = OrdenService(
            self.repo, None, transaction.atomic,
            total_estimacion=lambda version: D("150000.00"),
        )

    def test_resumen_por_elemento_proceso_y_total(self):
        self.mano_obra()
        self.costo(Elemento.DIRECTO, "500.00", proceso=self.programacion)
        self.costo(Elemento.INDIRECTO, "300.00", proceso=self.arte)
        anulado = self.costo(Elemento.DIRECTO, "999.00")
        self.servicio.anular(self.actor, registro_id=anulado.pk,
                             motivo="Error", clave="a-hoja")
        resumen = self.ordenes.resumen_orden(self.orden.pk)
        self.assertEqual(resumen["por_elemento"], {
            "MANO_OBRA": D("800.00"), "DIRECTO": D("500.00"),
            "INDIRECTO": D("300.00"),
        })
        self.assertEqual(resumen["por_proceso"], [
            {"proceso": "Arte", "importe": D("300.00")},
            {"proceso": "Programación", "importe": D("1300.00")},
        ])
        self.assertEqual(resumen["horas_por_proceso"],
                         [{"proceso": "Programación", "horas": D("40.00")}])
        self.assertEqual(resumen["total"], D("1600.00"))
        for clave_ in ("licencias_estimadas", "costo_unitario",
                       "estimacion_ref", "total_estimado"):
            self.assertIn(clave_, resumen)

    def test_costo_unitario_y_sin_licencias(self):
        self.assertEqual(calculos.costo_unitario(D("120000.00"), 60000),
                         D("2.0000"))
        self.assertIsNone(calculos.costo_unitario(D("10"), None))
        self.costo(Elemento.DIRECTO, "120000.00")
        self.assertIsNone(
            self.ordenes.resumen_orden(self.orden.pk)["costo_unitario"])
        self.ordenes.actualizar_licencias(self.actor, self.orden.pk, 60000)
        resumen = self.ordenes.resumen_orden(self.orden.pk)
        self.assertEqual(resumen["licencias_estimadas"], 60000)
        self.assertEqual(resumen["costo_unitario"], D("2.0000"))
        with self.assertRaises(DatosInsuficientesError):
            self.ordenes.actualizar_licencias(self.actor, self.orden.pk, 0)

    def test_actualizar_orden_edita_datos_operativos(self):
        nueva_fecha = date(2026, 5, 31)
        actualizada = self.ordenes.actualizar_orden(
            self.actor, self.orden.pk, nombre_juego="Neo Drift Remaster",
            fecha_inicio=nueva_fecha, licencias_estimadas=700,
        )
        self.assertEqual(actualizada.juego.nombre, "Neo Drift Remaster")
        self.assertEqual(actualizada.fecha_inicio, nueva_fecha)
        self.assertEqual(actualizada.licencias_estimadas, 700)

    def test_baja_logica_conserva_costos_y_permite_nueva_orden(self):
        registro = self.costo(Elemento.DIRECTO, "150.00")
        nombre_juego = self.orden.juego.nombre

        archivada = self.ordenes.eliminar(self.actor, self.orden.pk)

        self.assertTrue(archivada.eliminada)
        self.assertIsNotNone(archivada.eliminado_por)
        self.assertTrue(RegistroCosto.objects.filter(pk=registro.pk).exists())
        self.assertEqual(self.ordenes.listar(self.actor), [])
        self.assertEqual(
            len(self.ordenes.listar(
                self.actor, incluir_eliminadas=True
            )),
            1,
        )
        nueva = self.ordenes.crear_orden(
            self.actor, nombre_juego=nombre_juego, fecha_inicio=FECHA,
        )
        self.assertNotEqual(nueva.pk, archivada.pk)

        with self.assertRaises(OrdenDuplicadaError):
            self.ordenes.restaurar(self.actor, archivada.pk)
        self.ordenes.eliminar(self.actor, nueva.pk)

        restaurada = self.ordenes.restaurar(self.actor, archivada.pk)
        self.assertFalse(restaurada.eliminada)
        self.assertEqual(len(self.ordenes.listar(self.actor)), 1)

    def _version(self, estado, *, juego_nombre=None):
        from estimacion.models import Juego as JuegoEstimacion
        from estimacion.models import VersionPresupuesto
        juego, _ = JuegoEstimacion.objects.get_or_create(
            nombre=juego_nombre or self.orden.juego.nombre
        )
        return VersionPresupuesto.objects.create(
            juego=juego, numero=juego.versiones.count() + 1,
            estado=estado, autor=self.actor,
        )

    def test_estimacion_aprobada_muestra_total_sin_variacion(self):
        aprobada = self._version("APROBADO")
        self.ordenes.vincular_estimacion(self.actor, self.orden.pk,
                                         aprobada.pk)
        resumen = self.ordenes.resumen_orden(self.orden.pk)
        self.assertEqual(resumen["estimacion_ref"], aprobada)
        self.assertEqual(resumen["total_estimado"], D("150000.00"))
        self.assertNotIn("variacion", resumen)
        borrador = self._version("BORRADOR")
        self.assertIn(
            borrador.pk,
            [version.pk for version in self.ordenes.versiones_disponibles(
                self.actor, orden_id=self.orden.pk
            )],
        )
        self.ordenes.vincular_estimacion(
            self.actor, self.orden.pk, borrador.pk
        )
        self.assertEqual(self.ordenes.detalle(
            self.actor, self.orden.pk
        ).estimacion_ref, borrador)

    def test_crear_orden_vincula_estimacion_disponible(self):
        aprobada = self._version(
            "APROBADO", juego_nombre="Neo Aprobado"
        )

        orden = self.ordenes.crear_orden(
            self.actor, fecha_inicio=FECHA, estimacion_id=aprobada.pk,
        )

        self.assertEqual(orden.juego.nombre, aprobada.juego.nombre)
        self.assertEqual(orden.estimacion_ref, aprobada)

    def test_estimacion_vinculada_no_se_ofrece_para_otra_orden(self):
        aprobada = self._version("APROBADO")
        disponible = self._version("VIGENTE")
        rechazada = self._version("RECHAZADO")
        self.ordenes.vincular_estimacion(
            self.actor, self.orden.pk, aprobada.pk
        )

        versiones = self.ordenes.versiones_disponibles(self.actor)

        self.assertEqual([version.pk for version in versiones],
                         [disponible.pk])
        self.assertNotIn(rechazada.pk, [version.pk for version in versiones])
        with self.assertRaises(DatosInsuficientesError):
            self.ordenes.crear_orden(
                self.actor, nombre_juego="Otro juego", fecha_inicio=FECHA,
                estimacion_id=aprobada.pk,
            )

    def test_version_archivada_conserva_vinculo_historico_y_no_se_ofrece(self):
        from estimacion.composition import crear_presupuesto_service

        aprobada = self._version("APROBADO")
        self.ordenes.vincular_estimacion(
            self.actor, self.orden.pk, aprobada.pk
        )
        crear_presupuesto_service().eliminar_version(
            self.actor, aprobada.pk
        )

        self.assertEqual(
            self.ordenes.detalle(
                self.actor, self.orden.pk
            ).estimacion_ref_id,
            aprobada.pk,
        )
        self.assertNotIn(
            aprobada.pk,
            [v.pk for v in self.ordenes.versiones_disponibles(
                self.actor
            )],
        )

    def test_archivar_orden_libera_estimacion_sin_borrar_vinculo_historico(self):
        aprobada = self._version("APROBADO")
        self.ordenes.vincular_estimacion(
            self.actor, self.orden.pk, aprobada.pk
        )
        self.ordenes.eliminar(self.actor, self.orden.pk)

        disponibles = self.ordenes.versiones_disponibles(self.actor)
        self.assertIn(aprobada.pk, [version.pk for version in disponibles])
        self.assertEqual(
            OrdenTrabajo.objects.get(pk=self.orden.pk).estimacion_ref_id,
            aprobada.pk,
        )

    def test_estimacion_solo_puede_vincularse_a_una_orden(self):
        aprobada = self._version("APROBADO")
        otra_orden = self.ordenes.crear_orden(
            self.actor, nombre_juego="Otro juego", fecha_inicio=FECHA,
        )
        self.ordenes.vincular_estimacion(
            self.actor, self.orden.pk, aprobada.pk
        )

        with self.assertRaises(DatosInsuficientesError):
            self.ordenes.vincular_estimacion(
                self.actor, otra_orden.pk, aprobada.pk
            )

    def test_estimacion_libre_de_otro_juego_se_puede_vincular(self):
        aprobada = self._version(
            "APROBADO", juego_nombre="Otro videojuego"
        )

        opciones = self.ordenes.versiones_disponibles(
            self.actor, orden_id=self.orden.pk
        )
        self.assertIn(aprobada.pk, [version.pk for version in opciones])
        self.ordenes.vincular_estimacion(
            self.actor, self.orden.pk, aprobada.pk
        )
        self.assertEqual(self.ordenes.detalle(
            self.actor, self.orden.pk
        ).estimacion_ref, aprobada)

    def test_evaluacion_rendimiento_compara_costos_vigentes(self):
        aprobada = self._version("APROBADO")
        self.ordenes.vincular_estimacion(self.actor, self.orden.pk,
                                         aprobada.pk)
        self.costo(Elemento.DIRECTO, "500.00")
        anulado = self.costo(Elemento.DIRECTO, "100.00")
        self.servicio.anular(self.actor, registro_id=anulado.pk,
                             motivo="Duplicado", clave="evaluacion-anulado")

        evaluacion = self.ordenes.evaluar_rendimiento(
            self.actor, self.orden.pk
        )

        self.assertEqual(evaluacion["total_estimado"], D("150000.00"))
        self.assertEqual(evaluacion["total_real"], D("500.00"))
        self.assertEqual(evaluacion["variacion"], D("-149500.00"))
        self.assertEqual(evaluacion["porcentaje"], D("-99.67"))
        self.assertEqual(evaluacion["estado"], "POR_DEBAJO")

    def test_evaluacion_requiere_estimacion_vinculada(self):
        self.costo(Elemento.DIRECTO, "500.00")
        with self.assertRaises(DatosInsuficientesError):
            self.ordenes.evaluar_rendimiento(self.actor, self.orden.pk)

    def test_evaluacion_requiere_costos_vigentes(self):
        aprobada = self._version("APROBADO")
        self.ordenes.vincular_estimacion(self.actor, self.orden.pk,
                                         aprobada.pk)
        with self.assertRaises(DatosInsuficientesError):
            self.ordenes.evaluar_rendimiento(self.actor, self.orden.pk)

    def test_resultados_rendimiento_lista_orden_y_comparacion(self):
        aprobada = self._version("APROBADO")
        self.ordenes.vincular_estimacion(self.actor, self.orden.pk,
                                         aprobada.pk)
        self.costo(Elemento.DIRECTO, "500.00")

        resultados = self.ordenes.resultados_rendimiento(self.actor)

        self.assertEqual(len(resultados), 1)
        fila = resultados[0]
        self.assertEqual(fila["orden"], self.orden)
        self.assertEqual(fila["total_estimado"], D("150000.00"))
        self.assertEqual(fila["total_real"], D("500.00"))
        self.assertEqual(fila["evaluacion"]["estado"], "POR_DEBAJO")

    def test_resultados_rendimiento_indica_datos_pendientes(self):
        resultados = self.ordenes.resultados_rendimiento(self.actor)

        self.assertEqual(len(resultados), 1)
        self.assertIsNone(resultados[0]["total_estimado"])
        self.assertIsNone(resultados[0]["total_real"])
        self.assertIsNone(resultados[0]["evaluacion"])


class HojaVistaTests(VistasCostosTests):
    def test_hoja_con_secciones_vacias_y_sin_licencias(self):
        respuesta = self.client.get(reverse("costos_orden",
                                            args=[self.orden.pk]))
        for texto in ("Mano de obra directa", "Costo directo",
                      "Costo indirecto", "Sin registros de costo directo",
                      "Ingresa las licencias estimadas", "Imprimir"):
            self.assertContains(respuesta, texto)

    def test_hoja_muestra_total_y_costo_unitario(self):
        self.costo(Elemento.DIRECTO, "120000.00")
        respuesta = self.client.post(
            reverse("costos_orden_licencias", args=[self.orden.pk]),
            {"licencias_estimadas": "60000"},
        )
        self.assertRedirects(respuesta,
                             reverse("costos_orden", args=[self.orden.pk]))
        hoja = self.client.get(reverse("costos_orden", args=[self.orden.pk]))
        self.assertContains(hoja, "$120,000.00")
        self.assertContains(hoja, "$2.00")


class ConceptosEliminadosTests(SimpleTestCase):
    PROHIBIDOS = re.compile(
        r"cortes?_?costos|CorteCostos|corte provisional|costo_gestion|"
        r"costo de gesti[oó]n|afecta_mayor|fondo|"
        r"salario|sobreaplica|subaplica",
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
