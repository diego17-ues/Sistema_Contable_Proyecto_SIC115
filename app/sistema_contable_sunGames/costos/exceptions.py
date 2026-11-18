"""Excepciones de dominio del subsistema de costos (órdenes de trabajo)."""


class CostosError(Exception):
    """Base de los errores del módulo de costos."""

    def __init__(self, mensaje, *, campo=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo


class OrdenNoEncontradaError(CostosError):
    pass


class OrdenDuplicadaError(CostosError):
    pass


class OrdenCerradaError(CostosError):
    pass


class PeriodoNoAbiertoError(CostosError):
    pass


class ConfiguracionNoEncontradaError(CostosError):
    """El elemento no tiene cuentas configuradas: queda bloqueado."""


class CuentaNoValidaError(CostosError):
    pass


class ProcesoNoValidoError(CostosError):
    pass


class DatosInsuficientesError(CostosError):
    pass


class RegistroNoEncontradoError(CostosError):
    pass


class RegistroYaAnuladoError(CostosError):
    pass


class AsientoDescuadradoError(CostosError):
    pass


class ClaveIdempotenciaError(CostosError):
    """La clave ya se usó para otra operación distinta."""
