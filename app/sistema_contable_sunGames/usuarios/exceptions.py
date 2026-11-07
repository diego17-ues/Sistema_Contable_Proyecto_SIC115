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


class CredencialesInvalidasError(UsuarioError):
    mensaje = "Nombre de usuario o contraseña incorrectos."


class CuentaNoHabilitadaError(UsuarioInactivoError):
    mensaje = "La cuenta no está habilitada para iniciar sesión."


class ServicioAutenticacionError(UsuarioError):
    mensaje = "No se pudo iniciar sesión; intente nuevamente."


class AreaInicialPendienteError(UsuarioError):
    mensaje = "El área inicial de su rol todavía no está disponible."
