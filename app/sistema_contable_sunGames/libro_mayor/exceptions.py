class LibroMayorError(Exception):
    mensaje = "No se pudo completar la operación del Libro Mayor."

    def __init__(self, mensaje=None, *, campo=None, linea=None, lineas=()):
        super().__init__(mensaje or self.mensaje)
        self.campo = campo
        self.lineas = tuple(lineas) or ((linea,) if linea is not None else ())

    @property
    def linea(self):
        return self.lineas[0] if self.lineas else None


class CampoObligatorioError(LibroMayorError):
    mensaje = "Este campo es obligatorio."


class MovimientoInvalidoError(LibroMayorError):
    mensaje = "El movimiento no es válido."


class CuentaNoRegistrableError(LibroMayorError):
    mensaje = "La cuenta no admite registros."


class PeriodoCerradoError(LibroMayorError):
    mensaje = "El período de esa fecha está cerrado."


class FechaInvalidaError(LibroMayorError):
    mensaje = "La fecha no pertenece a un ejercicio registrado."


class ConceptoInvalidoError(LibroMayorError):
    mensaje = "El concepto no es válido."


class GuardadoTransaccionError(LibroMayorError):
    mensaje = (
        "No se pudieron guardar los movimientos; no se registró ningún "
        "cambio."
    )
