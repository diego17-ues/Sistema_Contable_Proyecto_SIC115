class CatalogoError(Exception):
    mensaje = "No se pudo completar la operación del catálogo."
    campo = None

    def __init__(self, mensaje=None, *, campo=None):
        super().__init__(mensaje or self.mensaje)
        if campo:
            self.campo = campo


class CuentaNoEncontradaError(CatalogoError):
    mensaje = "La cuenta no existe."


class CuentaDuplicadaError(CatalogoError):
    mensaje = "Ya existe una cuenta con esa denominación o una equivalente."
    campo = "denominacion"


class ClasificacionInvalidaError(CatalogoError):
    pass


class RubroInvalidoError(ClasificacionInvalidaError):
    mensaje = "El tipo de cuenta no pertenece al catálogo."
    campo = "rubro"


class NaturalezaInvalidaError(ClasificacionInvalidaError):
    mensaje = "La naturaleza no pertenece al catálogo."
    campo = "naturaleza"


class SubtipoInvalidoError(ClasificacionInvalidaError):
    mensaje = "El subtipo no pertenece al tipo de cuenta seleccionado."
    campo = "subtipo"


class DocumentacionIncompletaError(CatalogoError):
    mensaje = "Falta el respaldo o el acuerdo de Junta Directiva."


class CodigoNoAsignableError(CatalogoError):
    mensaje = (
        "No hay códigos disponibles en el subtipo: se usaron los 99 "
        "números. La cuenta no se registró."
    )


class CodigoInmodificableError(CatalogoError):
    mensaje = "El código de la cuenta es de solo lectura."


class SubcuentaNoPermitidaError(CatalogoError):
    mensaje = "El catálogo no admite subcuentas."


class SinCambiosError(CatalogoError):
    mensaje = "No hay cambios respecto de los valores actuales."


class GuardadoCuentaError(CatalogoError):
    mensaje = (
        "No se pudieron guardar los cambios; la cuenta conserva sus "
        "valores anteriores."
    )
