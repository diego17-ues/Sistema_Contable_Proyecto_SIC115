"""Servicios del subsistema de costos (órdenes de trabajo).

Reglas:
- Todo cargo queda en las tablas de ``costos``; NUNCA se escribe en el
  Libro Mayor (los asientos son una fase posterior).
- Los saldos capitalizables viven en la serie 41 (cuenta snapshot en el
  cargo) mientras el período está abierto; al corte/cierre se trasladan
  al intangible (MapeoCuenta ``intangible`` → p. ej. 1107).
- Período cerrado u orden cerrada rechazan cargos nuevos.
- Todo en ``Decimal``; nada de tasas, salarios ni cuentas en el código.
"""

import calendar
from contextlib import nullcontext
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from bitacora.eventos import Accion, Resultado
from libro_mayor.models import PeriodoContable
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol

from . import calculos
from .exceptions import (
    ConfirmacionError,
    CostosError,
    CorteNoEncontradoError,
    CuentaNoValidaError,
    DatosInsuficientesError,
    FondoYaDistribuidoError,
    JuegoNoEncontradoError,
    MapeoNoEncontradoError,
    OrdenCerradaError,
    OrdenNoEncontradaError,
    ParametroNoVigenteError,
    PeriodoNoAbiertoError,
    SalarioNoVigenteError,
    SinFechaCapitalizableError,
    SinHorasBaseError,
)
from .models import (
    CargoOrden,
    CONCEPTOS_CUENTA,
    CorteCostos,
    Equipo,
    FondoCompartido,
    OrdenTrabajo,
    Proceso,
)

ROLES_COSTOS = frozenset({
    Rol.ADMINISTRADOR, Rol.CONTADOR_GENERAL, "CONTADOR_COSTOS",
})
CENTAVO = Decimal("0.01")
CONFIRMACION = "CONFIRMAR"
ORIGENES_MANUALES = {
    CargoOrden.ORIGEN_DIRECTO,
    CargoOrden.ORIGEN_SERVICIO,
    CargoOrden.ORIGEN_AJUSTE,
}
CONCEPTO_POR_ORIGEN = {
    CargoOrden.ORIGEN_DIRECTO: "mano_obra",
    CargoOrden.ORIGEN_PROCESO: "indirecto",
    CargoOrden.ORIGEN_DEPRECIACION: "indirecto",
    CargoOrden.ORIGEN_AJUSTE: "indirecto",
}
PARAMETROS_LABOR = ("horas_semana", "semanas_año", "tasa_cargas_patronales")


def _verificar(actor):
    if not actor.activo:
        raise UsuarioInactivoError()
    if actor.rol not in ROLES_COSTOS:
        raise RolNoAutorizadoError()


def _q2(monto):
    return Decimal(monto).quantize(CENTAVO, rounding=ROUND_HALF_UP)


class CostosService:
    """Base: verificación de rol y helpers de período/mapeo."""

    def __init__(self, repositorio, bitacora, transaccion=nullcontext):
        self._repo = repositorio
        self._bitacora = bitacora
        self._transaccion = transaccion

    def puede(self, actor):
        return actor.activo and actor.rol in ROLES_COSTOS

    def _periodo_de_fecha(self, fecha):
        periodos = self._repo.periodos_de_fecha(fecha)
        if not periodos.exists():
            raise PeriodoNoAbiertoError(
                "No hay un período contable que cubra la fecha del cargo."
            )
        if any(p.cerrado for p in periodos):
            raise PeriodoNoAbiertoError(
                "El período contable de la fecha está cerrado."
            )
        return periodos.first()

    def _verificar_periodo_abierto(self, fecha):
        self._periodo_de_fecha(fecha)

    def _orden_abierta(self, orden):
        if not orden.abierta:
            raise OrdenCerradaError(
                "La orden de trabajo está cerrada; no admite cargos nuevos."
            )

    def _mapeo_cuenta(self, concepto):
        mapeo = self._repo.mapeo(concepto)
        if mapeo is None or mapeo.cuenta is None or not mapeo.cuenta.activa:
            raise MapeoNoEncontradoError(
                f"No hay cuenta configurada para «{concepto}» en el "
                "mapeo de costos."
            )
        return mapeo.cuenta

    def _es_capitalizable(self, orden, cargo):
        """Cargo que forma parte del costo capitalizable de la orden:
        afecta al mayor, tiene cuenta destino y su fecha es igual o
        posterior a ``capitalizable_desde`` (vacía → nada capitaliza)."""
        if not (cargo.afecta_mayor and cargo.cuenta_id):
            return False
        if orden.capitalizable_desde is None:
            return False
        return cargo.fecha >= orden.capitalizable_desde

    def _auditar(self, actor, accion, referencia, detalle=""):
        if self._bitacora is not None:
            self._bitacora.registrar(
                accion, Resultado.EXITOSO, actor=actor,
                referencia=(referencia or "")[:60], detalle=detalle,
            )


class OrdenService(CostosService):
    """Órdenes de trabajo: alta, horas, cargos y cierre."""

    def listar(self, actor, *, estado=None, juego_id=None):
        _verificar(actor)
        ordenes = list(self._repo.ordenes(estado=estado, juego_id=juego_id))
        for orden in ordenes:
            orden.saldos = self.saldos_orden(orden)
        return ordenes

    def detalle(self, actor, orden_id):
        _verificar(actor)
        try:
            orden = self._repo.obtener_orden(orden_id)
        except OrdenTrabajo.DoesNotExist as exc:
            raise OrdenNoEncontradaError() from exc
        return orden

    def crear_orden(self, actor, *, nombre_juego, capitalizable_desde=None):
        _verificar(actor)
        juego = self._repo.juego_por_nombre(nombre_juego)
        if juego is None:
            juego = self._repo.crear_juego(nombre=nombre_juego)
        if self._repo.orden_por_juego(juego) is not None:
            raise CostosError("El juego ya tiene una orden de trabajo.")
        with self._transaccion():
            orden = self._repo.crear_orden(
                juego=juego, capitalizable_desde=capitalizable_desde,
                usuario=actor,
            )
        self._auditar(actor, Accion.ORDEN_TRABAJO, f"OT-{orden.pk}",
                      f"Orden creada para {juego.nombre}")
        return orden

    # ---- Saldo de la orden ----
    def saldos_orden(self, orden):
        """Desglose de la orden: serie 41, corte vigente, intangible,
        gasto del período y costo de gestión (conciliación)."""
        cargos = list(self._repo.cargos_de_orden(orden))
        en_41 = en_corte = intangible = gasto = gestion_extra = Decimal("0")
        for cargo in cargos:
            if self._es_capitalizable(orden, cargo):
                if cargo.traslado_intangible:
                    intangible += cargo.monto
                elif (cargo.corte_id and cargo.corte
                      and cargo.corte.estado == CorteCostos.ESTADO_VIGENTE
                      and cargo.corte.tipo == CorteCostos.TIPO_PROVISIONAL):
                    en_corte += cargo.monto
                else:
                    en_41 += cargo.monto
            else:
                gasto += cargo.monto
                if not cargo.afecta_mayor:
                    gestion_extra += cargo.monto
        contable = en_41 + en_corte + intangible
        return {
            "en_41": en_41,
            "en_corte": en_corte,
            "intangible": intangible,
            "gasto_periodo": gasto,
            "costo_contable": contable,
            "costo_gestion": contable + gestion_extra,
        }

    # ---- Horas ----
    def registrar_hora(self, actor, orden_id, *, proceso_id=None, rol="",
                       horas=None, fecha=None):
        _verificar(actor)
        orden = self.detalle(actor, orden_id)
        self._orden_abierta(orden)
        self._verificar_periodo_abierto(fecha)
        with self._transaccion():
            hora = self._repo.crear_hora(
                orden=orden,
                proceso_id=proceso_id or None,
                rol=rol.strip(), horas=horas, fecha=fecha, usuario=actor,
            )
            cargo = self._cargo_mano_obra(actor, orden, hora)
        self._auditar(actor, Accion.CARGO_ORDEN, f"H-{hora.pk}",
                      f"{hora.horas} h de {hora.rol} en OT {orden.pk}")
        return hora, cargo

    def _cargo_mano_obra(self, actor, orden, hora):
        """Cargo DIRECTO de mano de obra por las horas registradas."""
        salario = self._repo.salario_vigente(hora.rol, hora.fecha)
        if salario is None:
            raise SalarioNoVigenteError(
                f"No hay salario de referencia vigente para «{hora.rol}» "
                f"en {hora.fecha:%d/%m/%Y}."
            )
        valores = {}
        for concepto in PARAMETROS_LABOR:
            parametro = self._repo.parametro_vigente(concepto, hora.fecha)
            if parametro is None:
                raise ParametroNoVigenteError(
                    f"Falta el parámetro «{concepto}» con vigencia en "
                    f"{hora.fecha:%d/%m/%Y}."
                )
            valores[concepto] = parametro.valor
        horas_mes = calculos.horas_mensuales(
            valores["horas_semana"], valores["semanas_año"]
        )
        costo_hora = calculos.costo_hora_pagada(
            salario.salario_bruto, valores["tasa_cargas_patronales"],
            horas_mes,
        )
        monto = _q2(Decimal(hora.horas) * costo_hora)
        cuenta = self._mapeo_cuenta("mano_obra")
        return self._repo.crear_cargo(
            orden=orden, origen=CargoOrden.ORIGEN_DIRECTO,
            concepto_cuenta="mano_obra", cuenta=cuenta,
            afecta_mayor=True, monto=monto, fecha=hora.fecha,
            descripcion=f"Mano de obra {hora.rol} · {hora.horas} h",
            registro_hora=hora,
            clave_idempotencia=f"hora-{hora.pk}",
            usuario=actor,
        )

    # ---- Cargos manuales ----
    def registrar_cargo(self, actor, orden_id, *, origen, afecta_mayor,
                        monto, fecha, descripcion, concepto_cuenta=""):
        _verificar(actor)
        if origen not in ORIGENES_MANUALES:
            raise CostosError("El origen del cargo no es válido.")
        orden = self.detalle(actor, orden_id)
        self._orden_abierta(orden)
        self._verificar_periodo_abierto(fecha)
        cuenta = None
        concepto = ""
        if afecta_mayor:
            concepto = concepto_cuenta or CONCEPTO_POR_ORIGEN.get(
                origen, "indirecto"
            )
            cuenta = self._mapeo_cuenta(concepto)
        with self._transaccion():
            cargo = self._repo.crear_cargo(
                orden=orden, origen=origen, concepto_cuenta=concepto,
                cuenta=cuenta, afecta_mayor=afecta_mayor,
                monto=_q2(monto), fecha=fecha,
                descripcion=descripcion.strip(), usuario=actor,
            )
        self._auditar(actor, Accion.CARGO_ORDEN, f"C-{cargo.pk}",
                      f"{cargo.get_origen_display()} ${cargo.monto} en OT {orden.pk}")
        return cargo

    # ---- Cierre de la orden (lanzamiento) ----
    def cerrar_orden(self, actor, orden_id, *, confirmacion, motivo):
        _verificar(actor)
        orden = self.detalle(actor, orden_id)
        if not orden.abierta:
            raise OrdenCerradaError("La orden ya está cerrada.")
        if (confirmacion or "").strip().upper() != CONFIRMACION:
            raise ConfirmacionError(
                'Escriba "CONFIRMAR" para cerrar la orden.', campo="confirmacion"
            )
        motivo = (motivo or "").strip()
        if not motivo:
            raise CostosError("El motivo de cierre es obligatorio.",
                              campo="motivo")
        hoy = timezone.localdate()
        self._verificar_periodo_abierto(hoy)
        with self._transaccion():
            for cargo in self._repo.cargos_capitalizables_sin_traslado(orden):
                cargo.traslado_intangible = hoy
                cargo.save(update_fields=["traslado_intangible"])
            orden.estado = OrdenTrabajo.ESTADO_CERRADA
            orden.fecha_cierre = hoy
            orden.motivo_cierre = motivo
            self._repo.guardar_orden(orden)
        self._auditar(actor, Accion.ORDEN_TRABAJO, f"OT-{orden.pk}",
                      f"Orden cerrada. Motivo: {motivo}")
        return orden


class CalculoService(CostosService):
    """Tasas por proceso, fondos compartidos, depreciación y cortes."""

    # ---- Costos de proceso por período ----
    def costos_proceso(self, actor, periodo_id=None):
        _verificar(actor)
        if periodo_id:
            periodo = self._repo.obtener_periodo(periodo_id)
        else:
            periodo = self._repo.periodo_abierto()
        if periodo is None:
            return [], None
        return list(self._repo.costos_proceso(periodo)), periodo

    def registrar_costo_proceso(self, actor, *, proceso_id, periodo_id,
                                costo, horas_base, tasa_presupuestada=None):
        _verificar(actor)
        try:
            proceso = self._repo.procesos().get(pk=proceso_id)
            periodo = self._repo.obtener_periodo(periodo_id)
        except (Proceso.DoesNotExist, PeriodoContable.DoesNotExist) as exc:
            raise CostosError("El proceso o el período no existe.") from exc
        if periodo.cerrado:
            raise PeriodoNoAbiertoError("El período está cerrado.")
        if not horas_base or Decimal(horas_base) <= 0:
            raise SinHorasBaseError(
                "Las horas base del proceso deben ser mayores que cero."
            )
        from django.db import IntegrityError
        try:
            with self._transaccion():
                costo_proceso = self._repo.crear_costo_proceso(
                    proceso=proceso, periodo=periodo, costo=_q2(costo),
                    horas_base=horas_base,
                    tasa_presupuestada=tasa_presupuestada,
                )
        except IntegrityError as exc:
            raise CostosError(
                "Ya existe un costo registrado para ese proceso y período."
            ) from exc
        self._auditar(actor, Accion.CATALOGO_COSTOS,
                      f"CP-{costo_proceso.pk}",
                      f"Costo {proceso.nombre} en {periodo}")
        return costo_proceso

    # ---- Tasas por proceso ----
    def aplicar_tasas(self, actor, periodo_id, *, usar_presupuestada=False):
        """Aplica la tasa de cada proceso del período a las horas de cada
        orden abierta y registra el ajuste de diferencia (sobre/sub
        aplicación) repartido por horas del proceso."""
        _verificar(actor)
        periodo = self._repo.obtener_periodo(periodo_id)
        if periodo.cerrado:
            raise PeriodoNoAbiertoError("El período está cerrado.")
        resultados = []
        with self._transaccion():
            for costo in self._repo.costos_proceso(periodo):
                resultados.append(self._aplicar_proceso(
                    actor, periodo, costo, usar_presupuestada
                ))
        return resultados

    def _aplicar_proceso(self, actor, periodo, costo, usar_presupuestada):
        proceso = costo.proceso
        if usar_presupuestada and costo.tasa_presupuestada is not None:
            tasa = costo.tasa_presupuestada
            origen_tasa = "presupuestada"
        else:
            if not costo.horas_base:
                raise SinHorasBaseError(
                    f"{proceso} no tiene horas base en {periodo}."
                )
            tasa = costo.tasa_real
            origen_tasa = "real"
        horas = {
            row["orden_id"]: row["total"]
            for row in self._repo.horas_en_periodo(proceso, periodo)
        }
        aplicados = {}
        cuenta = self._mapeo_cuenta("indirecto")
        for orden_id, total_horas in horas.items():
            monto = _q2(Decimal(total_horas) * Decimal(tasa))
            if monto == 0:
                continue
            clave = f"proc-{costo.pk}-{periodo.pk}-{orden_id}"
            if self._repo.cargo_por_clave(clave):
                continue
            orden = self._repo.obtener_orden(orden_id)
            self._repo.crear_cargo(
                orden=orden, origen=CargoOrden.ORIGEN_PROCESO,
                concepto_cuenta="indirecto", cuenta=cuenta,
                afecta_mayor=True, monto=monto,
                fecha=periodo.fecha_fin,
                descripcion=(
                    f"{proceso} · {total_horas} h × tasa {tasa} "
                    f"({origen_tasa})"
                ),
                proceso=proceso, clave_idempotencia=clave, usuario=actor,
            )
            aplicados[orden_id] = monto
        # Ajuste de diferencia contra el costo real del proceso. El total
        # aplicado se lee de los cargos existentes para que re-ejecutar
        # no duplique ni el cargo ni el ajuste.
        total_aplicado = self._repo.monto_proceso_aplicado(costo, periodo)
        diferencia = _q2(Decimal(costo.costo) - total_aplicado)
        if diferencia != 0:
            ordenes_ajuste = sorted(
                set(aplicados) | set(horas), key=int
            )
            cuotas = calculos.repartir(
                abs(diferencia), [horas[oid] for oid in ordenes_ajuste]
            )
            for orden_id, cuota in zip(ordenes_ajuste, cuotas):
                if cuota == 0:
                    continue
                clave = f"ajuste-proc-{costo.pk}-{periodo.pk}-{orden_id}"
                if self._repo.cargo_por_clave(clave):
                    continue
                orden = self._repo.obtener_orden(orden_id)
                self._repo.crear_cargo(
                    orden=orden, origen=CargoOrden.ORIGEN_AJUSTE,
                    concepto_cuenta="indirecto", cuenta=cuenta,
                    afecta_mayor=True,
                    monto=cuota if diferencia > 0 else -cuota,
                    fecha=periodo.fecha_fin,
                    descripcion=(
                        f"Ajuste {proceso}: {'sub' if diferencia > 0 else 'sobre'}"
                        f"aplicación ${abs(diferencia)}"
                    ),
                    proceso=proceso, clave_idempotencia=clave, usuario=actor,
                )
        self._auditar(actor, Accion.CARGO_ORDEN, f"TASA-{costo.pk}",
                      f"Tasa {proceso} aplicada ({origen_tasa})")
        return {"proceso": proceso.nombre, "tasa": tasa,
                "origen_tasa": origen_tasa, "aplicado": total_aplicado,
                "diferencia": diferencia}

    # ---- Fondos compartidos ----
    def crear_fondo(self, actor, *, nombre, monto, fecha, descripcion=""):
        _verificar(actor)
        self._verificar_periodo_abierto(fecha)
        with self._transaccion():
            fondo = self._repo.crear_fondo(
                nombre=nombre.strip(), monto=_q2(monto), fecha=fecha,
                descripcion=descripcion.strip(), creado_por=actor,
            )
        self._auditar(actor, Accion.FONDO_COMPARTIDO, f"F-{fondo.pk}",
                      f"Fondo {fondo.nombre} ${fondo.monto}")
        return fondo

    def distribuir_fondo(self, actor, fondo_id):
        """Reparte el fondo entre órdenes abiertas por horas de
        desarrollo; ajuste de centavos en la última orden. Solo una vez."""
        _verificar(actor)
        try:
            fondo = self._repo.obtener_fondo(fondo_id)
        except FondoCompartido.DoesNotExist as exc:
            raise CostosError("El fondo no existe.") from exc
        if fondo.estado == FondoCompartido.ESTADO_DISTRIBUIDO:
            raise FondoYaDistribuidoError(
                "El fondo ya fue distribuido; no se reparte de nuevo."
            )
        horas = {
            row["orden_id"]: row["total"]
            for row in self._repo.horas_por_orden(hasta=fondo.fecha)
        }
        if not horas or sum(horas.values(), Decimal("0")) <= 0:
            raise DatosInsuficientesError(
                "No hay horas de desarrollo registradas para repartir."
            )
        ordenes = [self._repo.obtener_orden(oid) for oid in horas]
        ordenes.sort(key=lambda o: o.pk)
        pesos = [horas[o.pk] for o in ordenes]
        cuotas = calculos.repartir(fondo.monto, pesos)
        with self._transaccion():
            for orden, cuota in zip(ordenes, cuotas):
                if cuota == 0:
                    continue
                self._repo.crear_cargo(
                    orden=orden, origen=CargoOrden.ORIGEN_SERVICIO,
                    afecta_mayor=False, monto=_q2(cuota), fecha=fondo.fecha,
                    descripcion=f"Fondo compartido: {fondo.nombre}",
                    fondo=fondo,
                    clave_idempotencia=f"fondo-{fondo.pk}-{orden.pk}",
                    usuario=actor,
                )
            fondo.estado = FondoCompartido.ESTADO_DISTRIBUIDO
            self._repo.guardar_fondo(fondo)
        self._auditar(actor, Accion.FONDO_COMPARTIDO, f"F-{fondo.pk}",
                      "Fondo distribuido entre órdenes")
        return fondo

    # ---- Depreciación línea recta ----
    def generar_depreciacion(self, actor, *, anio, mes):
        """Genera los cargos DEPRECIACION del mes para cada equipo activo.

        - Exclusivo: cuota completa a su orden.
        - Compartido: cuota repartida por horas máquina del mes.
        - Administración/ocioso: no genera cargo en órdenes.
        """
        _verificar(actor)
        ultimo = calendar.monthrange(anio, mes)[1]
        fecha = date(anio, mes, ultimo)
        self._verificar_periodo_abierto(fecha)
        generados = []
        with self._transaccion():
            for equipo in self._repo.equipos():
                if not equipo.activo:
                    continue
                cuota = equipo.cuota_mensual
                if not cuota or cuota <= 0:
                    continue
                cuota = _q2(cuota)
                if equipo.tipo_uso == "EXCLUSIVO":
                    generados += self._depreciacion_exclusiva(
                        actor, equipo, cuota, anio, mes, fecha
                    )
                elif equipo.tipo_uso == "COMPARTIDO":
                    generados += self._depreciacion_compartida(
                        actor, equipo, cuota, anio, mes, fecha
                    )
                # ADMINISTRACION y OCIOSO: sin cargo en órdenes.
        if generados:
            self._auditar(actor, Accion.EQUIPO_COSTOS,
                          f"DEP-{anio}-{mes:02d}",
                          f"{len(generados)} cargo(s) de depreciación")
        return generados

    def _depreciacion_exclusiva(self, actor, equipo, cuota, anio, mes,
                                fecha):
        if equipo.orden is None or not equipo.orden.abierta:
            return []
        clave = f"dep-{equipo.pk}-{anio}-{mes:02d}"
        if self._repo.cargo_por_clave(clave):
            return []
        cuenta = self._mapeo_cuenta("indirecto")
        self._repo.crear_cargo(
            orden=equipo.orden, origen=CargoOrden.ORIGEN_DEPRECIACION,
            concepto_cuenta="indirecto", cuenta=cuenta, afecta_mayor=True,
            monto=cuota, fecha=fecha,
            descripcion=f"Depreciación {equipo.nombre} (uso exclusivo)",
            equipo=equipo, clave_idempotencia=clave, usuario=actor,
        )
        return [f"{equipo.nombre} → OT {equipo.orden_id}: ${cuota}"]

    def _depreciacion_compartida(self, actor, equipo, cuota, anio, mes,
                                 fecha):
        """Tasa por hora máquina = cuota mensual / horas_mes. La capacidad
        no usada (horas_mes − horas registradas) queda fuera de las
        órdenes: es capacidad ociosa."""
        if not equipo.horas_mes:
            return []
        tasa_hora = cuota / equipo.horas_mes
        usos = {
            row["orden_id"]: row["total"]
            for row in self._repo.usos_en_mes(equipo, anio, mes)
        }
        if not usos:
            return []  # sin uso registrado: todo el equipo está ocioso
        cuenta = self._mapeo_cuenta("indirecto")
        salida = []
        for orden_id, horas in sorted(usos.items()):
            parte = _q2(Decimal(horas) * tasa_hora)
            if parte == 0:
                continue
            clave = f"dep-{equipo.pk}-{anio}-{mes:02d}-{orden_id}"
            if self._repo.cargo_por_clave(clave):
                continue
            orden = self._repo.obtener_orden(orden_id)
            self._repo.crear_cargo(
                orden=orden, origen=CargoOrden.ORIGEN_DEPRECIACION,
                concepto_cuenta="indirecto", cuenta=cuenta,
                afecta_mayor=True, monto=parte, fecha=fecha,
                descripcion=f"Depreciación {equipo.nombre} (compartido)",
                equipo=equipo, clave_idempotencia=clave, usuario=actor,
            )
            salida.append(f"{equipo.nombre} → OT {orden_id}: ${parte}")
        return salida

    # ---- Cortes de costos ----
    def crear_corte(self, actor, *, periodo_id, tipo, motivo):
        """Corte provisional (reversible) o definitivo del período.

        Traslada los saldos capitalizables vigentes de la serie 41 al
        intangible. No toca el Libro Mayor ni cierra el período.
        """
        _verificar(actor)
        try:
            periodo = self._repo.obtener_periodo(periodo_id)
        except PeriodoContable.DoesNotExist as exc:
            raise CostosError("El período no existe.") from exc
        if tipo == CorteCostos.TIPO_PROVISIONAL and periodo.cerrado:
            raise PeriodoNoAbiertoError(
                "No se puede hacer un corte provisional en un período "
                "cerrado."
            )
        if tipo not in (CorteCostos.TIPO_PROVISIONAL,
                        CorteCostos.TIPO_DEFINITIVO):
            raise CostosError("El tipo de corte no es válido.")
        motivo = (motivo or "").strip()
        if not motivo:
            raise CostosError("El motivo del corte es obligatorio.",
                              campo="motivo")
        fecha = timezone.localdate()
        with self._transaccion():
            corte = self._repo.crear_corte(
                periodo=periodo, tipo=tipo, fecha=fecha, motivo=motivo,
                usuario=actor,
            )
            self._aplicar_corte(corte)
        self._auditar(actor, Accion.CORTE_COSTOS, f"CORTE-{corte.pk}",
                      f"Corte {tipo} · {periodo} · {motivo}")
        return corte

    def _aplicar_corte(self, corte):
        """Marca los cargos capitalizables pendientes hasta la fecha del
        corte y guarda el detalle por orden y cuenta."""
        pendientes = [
            c for c in self._repo.cargos_para_corte(corte.fecha)
            if self._es_capitalizable(c.orden, c)
        ]
        agrupado = {}
        for cargo in pendientes:
            clave = (cargo.orden_id, cargo.cuenta_id)
            agrupado[clave] = agrupado.get(clave, Decimal("0")) + cargo.monto
            if corte.tipo == CorteCostos.TIPO_PROVISIONAL:
                cargo.corte = corte
            else:
                cargo.traslado_intangible = corte.fecha
            self._repo.guardar_cargo(cargo)
        for (orden_id, cuenta_id), monto in agrupado.items():
            self._repo.crear_detalle_corte(
                corte=corte, orden_id=orden_id, cuenta_id=cuenta_id,
                monto=monto,
            )
        return agrupado

    def revertir_corte(self, actor, corte_id):
        """Revierte un corte provisional: los saldos vuelven a la 41."""
        _verificar(actor)
        try:
            corte = self._repo.obtener_corte(corte_id)
        except CorteCostos.DoesNotExist as exc:
            raise CorteNoEncontradoError() from exc
        if corte.tipo != CorteCostos.TIPO_PROVISIONAL:
            raise CostosError("Solo los cortes provisionales se revierten.")
        if corte.estado == CorteCostos.ESTADO_REVERTIDO:
            raise CostosError("El corte ya fue revertido.")
        with self._transaccion():
            for cargo in corte.cargos.select_related("orden"):
                if (cargo.traslado_intangible is None
                        and self._es_capitalizable(cargo.orden, cargo)):
                    cargo.corte = None
                    cargo.save(update_fields=["corte"])
            corte.estado = CorteCostos.ESTADO_REVERTIDO
            self._repo.guardar_corte(corte)
        self._auditar(actor, Accion.CORTE_COSTOS, f"CORTE-{corte.pk}",
                      "Corte provisional revertido")
        return corte


class CatalogoCostosService(CostosService):
    """Catálogos del módulo: procesos, parámetros, salarios y mapeos."""

    def procesos(self, actor):
        _verificar(actor)
        return self._repo.procesos()

    def crear_proceso(self, actor, *, nombre, descripcion=""):
        _verificar(actor)
        with self._transaccion():
            proceso = self._repo.crear_proceso(
                nombre=nombre, descripcion=descripcion
            )
        self._auditar(actor, Accion.CATALOGO_COSTOS, f"PRO-{proceso.pk}",
                      f"Proceso {proceso.nombre}")
        return proceso

    def parametros(self, actor):
        _verificar(actor)
        return self._repo.parametros()

    def crear_parametro(self, actor, **datos):
        _verificar(actor)
        with self._transaccion():
            parametro = self._repo.crear_parametro(**datos)
        self._auditar(actor, Accion.CATALOGO_COSTOS,
                      f"PAR-{parametro.pk}",
                      f"Parámetro {parametro.concepto}")
        return parametro

    def salarios(self, actor):
        _verificar(actor)
        return self._repo.salarios()

    def crear_salario(self, actor, **datos):
        _verificar(actor)
        with self._transaccion():
            salario = self._repo.crear_salario(**datos)
        self._auditar(actor, Accion.CATALOGO_COSTOS, f"SAL-{salario.pk}",
                      f"Salario {salario.rol}")
        return salario

    def mapeos(self, actor):
        _verificar(actor)
        return self._repo.mapeos()

    def crear_mapeo(self, actor, *, concepto, cuenta_codigo):
        _verificar(actor)
        if concepto not in dict(CONCEPTOS_CUENTA):
            raise CostosError("El concepto de cuenta no es válido.")
        cuenta = self._repo.cuenta(cuenta_codigo)
        if cuenta is None or not cuenta.activa:
            raise CuentaNoValidaError(
                "La cuenta no existe o está inactiva en el catálogo.",
                campo="cuenta",
            )
        with self._transaccion():
            mapeo = self._repo.crear_mapeo(concepto=concepto, cuenta=cuenta)
        self._auditar(actor, Accion.CATALOGO_COSTOS, f"MAP-{mapeo.pk}",
                      f"{mapeo.concepto} → {cuenta.codigo}")
        return mapeo

    def fondos(self, actor):
        _verificar(actor)
        return self._repo.fondos()

    def equipos(self, actor):
        _verificar(actor)
        return self._repo.equipos()

    def crear_equipo(self, actor, **datos):
        _verificar(actor)
        with self._transaccion():
            equipo = self._repo.crear_equipo(**datos)
        self._auditar(actor, Accion.EQUIPO_COSTOS, f"EQ-{equipo.pk}",
                      f"Equipo {equipo.nombre}")
        return equipo

    def crear_uso_equipo(self, actor, *, equipo_id, orden_id, fecha, horas):
        _verificar(actor)
        try:
            equipo = self._repo.obtener_equipo(equipo_id)
            orden = self._repo.obtener_orden(orden_id)
        except (Equipo.DoesNotExist, OrdenTrabajo.DoesNotExist) as exc:
            raise CostosError("El equipo o la orden no existe.") from exc
        if not equipo.activo:
            raise CostosError("El equipo está inactivo.")
        if not orden.abierta:
            raise OrdenCerradaError("La orden está cerrada.")
        self._verificar_periodo_abierto(fecha)
        with self._transaccion():
            uso = self._repo.crear_uso_equipo(
                equipo=equipo, orden=orden, fecha=fecha, horas=horas,
            )
        self._auditar(actor, Accion.EQUIPO_COSTOS, f"USO-{uso.pk}",
                      f"{horas} h máquina en OT {orden.pk}")
        return uso

    def cuentas_posteables(self, actor):
        _verificar(actor)
        return self._repo.cuentas_posteables()

    def ordenes_abiertas(self, actor):
        _verificar(actor)
        return self._repo.ordenes(estado=OrdenTrabajo.ESTADO_ABIERTA)

    def periodos(self, actor):
        _verificar(actor)
        return self._repo.periodos()

    def cortes(self, actor):
        _verificar(actor)
        return self._repo.cortes()
