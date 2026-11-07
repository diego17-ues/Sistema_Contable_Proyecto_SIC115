class UsuarioError(Exception):
    mensaje = "No se pudo completar la operación sobre el usuario."

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)


class UsuarioDuplicadoError(UsuarioError):
    mensaje = "El nombre de usuario ya está registrado."


class RolNoAutorizadoError(UsuarioError):
    mensaje = "Su rol no está autorizado para realizar esta acción."


class UsuarioInactivoError(UsuarioError):
    mensaje = "El usuario está inactivo."


class RolInvalidoError(UsuarioError):
    mensaje = "Seleccione un rol permitido."


class UsuarioNoEncontradoError(UsuarioError):
    mensaje = "El usuario seleccionado no existe."
