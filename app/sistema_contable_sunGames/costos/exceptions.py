"""Excepciones de dominio del subsistema de costos (órdenes de trabajo)."""


class CostosError(Exception):
    """Base de los errores del módulo de costos."""

    def __init__(self, mensaje, *, campo=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo


class OrdenNoEncontradaError(CostosError):
    pass


class JuegoNoEncontradoError(CostosError):
    pass


class OrdenCerradaError(CostosError):
    pass


class PeriodoNoAbiertoError(CostosError):
    pass


class SinFechaCapitalizableError(CostosError):
    pass


class ParametroNoVigenteError(CostosError):
    pass


class SalarioNoVigenteError(CostosError):
    pass


class MapeoNoEncontradoError(CostosError):
    pass


class CuentaNoValidaError(CostosError):
    pass


class FondoYaDistribuidoError(CostosError):
    pass


class SinHorasBaseError(CostosError):
    pass


class CorteNoEncontradoError(CostosError):
    pass


class ConfirmacionError(CostosError):
    pass


class DatosInsuficientesError(CostosError):
    pass
