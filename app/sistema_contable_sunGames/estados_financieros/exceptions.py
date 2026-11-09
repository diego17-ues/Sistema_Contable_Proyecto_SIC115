class EstadosFinancierosError(Exception):
    mensaje = "No se pudo completar la operación de estados financieros."

    def __init__(self, mensaje=None, *, campo=None):
        super().__init__(mensaje or self.mensaje)
        self.campo = campo


class PeriodoNoEncontradoError(EstadosFinancierosError):
    mensaje = "El período contable no existe."


class TipoEstadoInvalidoError(EstadosFinancierosError):
    mensaje = "El estado financiero solicitado no existe."


class RecalculoPeriodoCerradoError(EstadosFinancierosError):
    mensaje = (
        "El período está cerrado: sus estados financieros no se generan "
        "ni se recalculan; se consulta el emitido al cerrar."
    )


class SnapshotNoDisponibleError(EstadosFinancierosError):
    mensaje = "El período cerrado no tiene un estado emitido al cierre."


class EstadoInmutableError(EstadosFinancierosError):
    mensaje = "Un estado financiero emitido no se modifica ni se elimina."


class PeriodoNoAbiertoError(EstadosFinancierosError):
    mensaje = "El período no está abierto; no se puede cerrar."


class ConfirmacionIncorrectaError(EstadosFinancierosError):
    mensaje = "Escribe el nombre exacto del período para confirmar."


class MotivoObligatorioError(EstadosFinancierosError):
    mensaje = "El motivo es obligatorio."


class BalanzaDescuadradaError(EstadosFinancierosError):
    mensaje = "La balanza de comprobación no cuadra; no se puede cerrar."


class ContrasenaIncorrectaError(EstadosFinancierosError):
    mensaje = "La contraseña no es correcta; el período sigue cerrado."


class PeriodoNoReabribleError(EstadosFinancierosError):
    mensaje = "El período no tiene un cierre provisional que reabrir."


class GuardadoCierreError(EstadosFinancierosError):
    mensaje = "No se pudo guardar; el período quedó como estaba."
