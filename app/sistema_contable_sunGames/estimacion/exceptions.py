class EstimacionError(Exception):
    mensaje = "No se pudo completar la operación de estimación."

    def __init__(self, mensaje=None, *, campo=None):
        self.campo = campo
        super().__init__(mensaje or self.mensaje)


class JuegoNoEncontradoError(EstimacionError):
    mensaje = "El juego seleccionado no existe."


class RolNoEncontradoError(EstimacionError):
    mensaje = "El rol seleccionado no existe."


class SalarioNoEncontradoError(EstimacionError):
    mensaje = "No hay salario de referencia vigente para el rol en la fecha."


class ExpertoNoEncontradoError(EstimacionError):
    mensaje = "El experto seleccionado no existe."


class FaseNoEncontradaError(EstimacionError):
    mensaje = "La fase seleccionada no existe."


class EstimacionInvalidaError(EstimacionError):
    mensaje = "La estimación no cumple O ≤ M ≤ P ni valores negativos."


class RondaNoEncontradaError(EstimacionError):
    mensaje = "La ronda Delphi seleccionada no existe."


class RondaCerradaError(EstimacionError):
    mensaje = "La ronda ya está cerrada; no admite nuevas estimaciones."


class RondaSinAprobarError(EstimacionError):
    mensaje = "Una ronda no se cierra sin aprobación registrada."


class ParametroInvalidoError(EstimacionError):
    mensaje = "El parámetro no es válido."


class VersionInmutableError(EstimacionError):
    mensaje = (
        "La versión está aprobada o vigente y es inmutable; "
        "registre una versión nueva."
    )


class VersionNoEncontradaError(EstimacionError):
    mensaje = "La versión de presupuesto seleccionada no existe."


class SinRondaAprobadaError(EstimacionError):
    mensaje = "El juego no tiene una ronda Delphi cerrada y aprobada."
