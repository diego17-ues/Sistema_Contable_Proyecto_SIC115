"""CU-07 Estados financieros y cierre provisional de períodos.

Un período cerrado no genera ni recalcula estados: al cerrar se guarda un
snapshot inmutable (``EstadoFinancieroEmitido``) y después se consulta y
exporta ese snapshot. Solo la reapertura, reservada al Administrador y
confirmada con su contraseña, devuelve el período a Abierto.
"""

from contextlib import nullcontext
from dataclasses import dataclass
from decimal import Decimal

from bitacora.eventos import Accion, Resultado
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol

from . import calculo
from .exceptions import (
    BalanzaDescuadradaError,
    ConfirmacionIncorrectaError,
    ContrasenaIncorrectaError,
    EstadosFinancierosError,
    GuardadoCierreError,
    MotivoObligatorioError,
    PeriodoNoAbiertoError,
    PeriodoNoReabribleError,
    RecalculoPeriodoCerradoError,
    SnapshotNoDisponibleError,
    TipoEstadoInvalidoError,
)
from .models import TipoEstado

CERO = Decimal("0.00")
MOTIVO_MAX = 300
DETALLE_MAX = 500
ROLES_CONSULTA = frozenset({Rol.CONTADOR_GENERAL, Rol.ADMINISTRADOR})


def _verificar(actor, roles):
    if not actor.activo:
        raise UsuarioInactivoError()
    if actor.rol not in roles:
        raise RolNoAutorizadoError()


def _referencia(periodo):
    return f"Período {periodo.nombre}"[:60]


@dataclass(frozen=True)
class EstadoConsultado:
    periodo: object
    datos: dict
    emitido: object = None

    @property
    def desde_snapshot(self):
        return self.emitido is not None


class EstadosFinancierosService:
    def __init__(self, repositorio, bitacora, exportador=None):
        self._repositorio = repositorio
        self._bitacora = bitacora
        self._exportador = exportador

    def calcular(self, periodo, tipo):
        if periodo.cerrado:
            raise RecalculoPeriodoCerradoError(
                f"El período «{periodo.nombre}» está cerrado "
                f"({periodo.get_estado_display().lower()}): sus estados "
                "financieros no se generan ni se recalculan; se consulta "
                "el emitido al cerrar."
            )
        if tipo == TipoEstado.BALANCE_GENERAL:
            return calculo.balance_general(
                periodo, self._repositorio.saldos(hasta=periodo.fecha_fin)
            )
        if tipo == TipoEstado.ESTADO_RESULTADOS:
            return calculo.estado_resultados(periodo, self._repositorio.saldos(
                desde=periodo.fecha_inicio, hasta=periodo.fecha_fin
            ))
        raise TipoEstadoInvalidoError()

    def calcular_todos(self, periodo):
        return {tipo: self.calcular(periodo, tipo) for tipo in TipoEstado}

    def generar_por_comando(self, referencia):
        periodo = self._repositorio.buscar_periodo(referencia)
        try:
            estados = self.calcular_todos(periodo)
        except RecalculoPeriodoCerradoError as error:
            self._bitacora.registrar(
                Accion.EMISION_ESTADOS, Resultado.RECHAZADO,
                referencia=_referencia(periodo),
                detalle=f"Comando estados_financieros: {error}",
            )
            raise
        self._bitacora.registrar(
            Accion.EMISION_ESTADOS, Resultado.EXITOSO,
            referencia=_referencia(periodo),
            detalle="Comando estados_financieros: cálculo del período "
                    "abierto, sin snapshot.",
        )
        return periodo, estados

    def obtener(self, actor, periodo_id, tipo):
        _verificar(actor, ROLES_CONSULTA)
        if tipo not in TipoEstado.values:
            raise TipoEstadoInvalidoError()
        periodo = self._repositorio.obtener_periodo(periodo_id)
        if not periodo.cerrado:
            return EstadoConsultado(periodo, self.calcular(periodo, tipo))
        emitido = self._repositorio.ultimo_emitido(periodo, tipo)
        if emitido is None:
            raise SnapshotNoDisponibleError()
        return EstadoConsultado(periodo, emitido.datos, emitido)

    def exportar_pdf(self, actor, periodo_id, tipo):
        consulta = self.obtener(actor, periodo_id, tipo)
        periodo = consulta.periodo
        archivo = self._exportador.exportar(
            consulta.datos, estado_periodo=periodo.get_estado_display(),
            fecha_emision=(consulta.emitido.fecha_emision
                           if consulta.desde_snapshot else None),
        )
        origen = ("snapshot emitido al cierre" if consulta.desde_snapshot
                  else "cálculo del período abierto")
        self._bitacora.registrar(
            Accion.DESCARGA_ESTADO_PDF, Resultado.EXITOSO, actor=actor,
            referencia=_referencia(periodo),
            detalle=f"{TipoEstado(tipo).label}; origen: {origen}.",
        )
        return archivo


@dataclass(frozen=True)
class ResumenCierre:
    periodo: object
    transacciones: int
    movimientos: int
    diferencia: Decimal

    @property
    def cuadra(self):
        return self.diferencia == 0

    @property
    def diferencia_absoluta(self):
        return abs(self.diferencia)


class CierrePeriodoService:
    ROLES_CIERRE = frozenset({Rol.CONTADOR_GENERAL})
    ROLES_REAPERTURA = frozenset({Rol.ADMINISTRADOR})

    def __init__(self, repositorio, estados, bitacora,
                 transaccion=nullcontext):
        self._repositorio = repositorio
        self._estados = estados
        self._bitacora = bitacora
        self._transaccion = transaccion

    def puede_cerrar(self, actor):
        return actor.activo and actor.rol in self.ROLES_CIERRE

    def puede_reabrir(self, actor):
        return actor.activo and actor.rol in self.ROLES_REAPERTURA

    def resumenes(self, actor):
        _verificar(actor, ROLES_CONSULTA)
        return [self._resumen(p) for p in self._repositorio.periodos()]

    def cerrar(self, actor, periodo_id, *, confirmacion, motivo):
        _verificar(actor, self.ROLES_CIERRE)
        periodo = self._repositorio.obtener_periodo(periodo_id)
        motivo = (motivo or "").strip()
        try:
            self._validar_cierre(periodo, confirmacion, motivo)
        except EstadosFinancierosError as error:
            self._registrar(Accion.CIERRE_PERIODO, Resultado.RECHAZADO, actor,
                            periodo, f"{error} Motivo: {motivo or '—'}")
            raise
        try:
            with self._transaccion():
                self._emitir_y_cerrar(actor, periodo, motivo)
        except GuardadoCierreError:
            raise
        except Exception as exc:  # noqa: BLE001 - cualquier fallo revierte
            raise GuardadoCierreError() from exc
        return periodo

    def registrar_reapertura_denegada(self, actor, periodo_id):
        periodo = self._repositorio.obtener_periodo(periodo_id)
        self._registrar(Accion.REAPERTURA_PERIODO, Resultado.RECHAZADO, actor,
                        periodo, "Solo un administrador puede reabrir.")

    def reabrir(self, actor, periodo_id, *, contrasena, motivo):
        if not self.puede_reabrir(actor):
            self.registrar_reapertura_denegada(actor, periodo_id)
            _verificar(actor, self.ROLES_REAPERTURA)
        periodo = self._repositorio.obtener_periodo(periodo_id)
        motivo = (motivo or "").strip()
        try:
            if not periodo.cerrado:
                raise PeriodoNoReabribleError()
            self._validar_motivo(motivo)
        except EstadosFinancierosError as error:
            self._registrar(Accion.REAPERTURA_PERIODO, Resultado.RECHAZADO,
                            actor, periodo, f"{error} Motivo: {motivo or '—'}")
            raise
        if not contrasena or not actor.check_password(contrasena):
            self._registrar(
                Accion.REAPERTURA_PERIODO, Resultado.CREDENCIALES_INCORRECTAS,
                actor, periodo, f"Contraseña incorrecta. Motivo: {motivo}",
            )
            raise ContrasenaIncorrectaError(campo="contrasena")
        with self._transaccion():
            self._repositorio.reabrir(periodo)
            self._registrar(Accion.REAPERTURA_PERIODO, Resultado.EXITOSO,
                            actor, periodo, f"Motivo: {motivo}")
        return periodo

    def _resumen(self, periodo):
        transacciones, movimientos = self._repositorio.conteo(periodo)
        suma = self._repositorio.suma_balanza(hasta=periodo.fecha_fin)
        return ResumenCierre(periodo, transacciones, movimientos,
                             suma or CERO)

    def _validar_cierre(self, periodo, confirmacion, motivo):
        if periodo.cerrado:
            raise PeriodoNoAbiertoError()
        self._validar_motivo(motivo)
        if (confirmacion or "").strip() != periodo.nombre:
            raise ConfirmacionIncorrectaError(campo="confirmacion")
        resumen = self._resumen(periodo)
        if not resumen.cuadra:
            raise BalanzaDescuadradaError(
                "La balanza de comprobación no cuadra (diferencia "
                f"${resumen.diferencia_absoluta:,.2f}); no se puede cerrar."
            )

    @staticmethod
    def _validar_motivo(motivo):
        if not motivo:
            raise MotivoObligatorioError(campo="motivo")
        if len(motivo) > MOTIVO_MAX:
            raise MotivoObligatorioError(
                f"El motivo admite hasta {MOTIVO_MAX} caracteres.",
                campo="motivo",
            )

    def _emitir_y_cerrar(self, actor, periodo, motivo):
        for tipo, datos in self._estados.calcular_todos(periodo).items():
            self._repositorio.guardar_emitido(
                periodo=periodo, tipo=tipo, datos=datos, usuario=actor
            )
        self._repositorio.cerrar(periodo)
        self._registrar(Accion.CIERRE_PERIODO, Resultado.EXITOSO, actor,
                        periodo, f"Motivo: {motivo}")
        self._registrar(
            Accion.EMISION_ESTADOS, Resultado.EXITOSO, actor, periodo,
            "Snapshot inmutable al cierre: Balance General y Estado de "
            "Resultados.",
        )

    def _registrar(self, accion, resultado, actor, periodo, detalle):
        self._bitacora.registrar(
            accion, resultado, actor=actor, referencia=_referencia(periodo),
            detalle=detalle[:DETALLE_MAX],
        )
