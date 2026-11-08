from usuarios.exceptions import UsuarioNoEncontradoError
from usuarios.models import Usuario
from usuarios.roles import Rol


class UsuarioRepositoryEnMemoria:
    """Implementación en memoria de la interfaz de UsuarioRepository."""

    def __init__(self, usuarios=()):
        self._usuarios = {u.username: u for u in usuarios}

    def existe_username(self, username):
        return username in self._usuarios

    def obtener_por_username(self, username):
        try:
            return self._usuarios[username]
        except KeyError as exc:
            raise UsuarioNoEncontradoError() from exc

    def listar(self):
        return [self._usuarios[k] for k in sorted(self._usuarios)]

    def nuevo(self, *, username, nombre_completo, rol):
        return Usuario(
            username=username, nombre_completo=nombre_completo, rol=rol
        )

    def guardar(self, usuario):
        self._usuarios[usuario.username] = usuario
        return usuario

    def actualizar_estado(self, usuario, *, activo):
        usuario.activo = activo
        return usuario


def crear_usuario(username="admin", rol=Rol.ADMINISTRADOR, activo=True):
    return Usuario(
        username=username,
        nombre_completo=f"Nombre {username}",
        rol=rol,
        activo=activo,
    )
