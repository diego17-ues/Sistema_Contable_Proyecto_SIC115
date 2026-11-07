from .exceptions import (
    RolInvalidoError,
    RolNoAutorizadoError,
    UsuarioDuplicadoError,
    UsuarioInactivoError,
)
from .roles import Rol


class UsuarioService:
    """Casos de uso de CU-02 Administrar Usuarios."""

    ROLES_ASIGNABLES = frozenset(Rol.values)

    def __init__(self, repositorio):
        self._repositorio = repositorio

    def agregar(self, actor, *, username, nombre_completo, rol):
        """CU-02.1: registra un usuario activo con el rol indicado."""
        self._verificar_administrador(actor)
        self._validar_rol(rol)
        self._validar_username_disponible(username)
        # TODO(CU-02.1): definir cómo se establece la contraseña de usuarios
        # nuevos (pendiente de definir en AGENT.md).
        # TODO(CU-03): registrar el alta en la bitácora mediante
        # AuditoriaService, dentro de transaction.atomic().
        return self._repositorio.crear(
            username=username, nombre_completo=nombre_completo, rol=rol
        )

    def desactivar(self, actor, username):
        """CU-02.2: cambia el estado a inactivo; el registro se conserva."""
        self._verificar_administrador(actor)
        usuario = self._repositorio.obtener_por_username(username)
        if not usuario.activo:
            raise UsuarioInactivoError("El usuario ya está inactivo.")
        # TODO(CU-03): registrar la desactivación en la bitácora mediante
        # AuditoriaService, dentro de transaction.atomic().
        return self._repositorio.actualizar_estado(usuario, activo=False)

    def listar(self, actor):
        """CU-02.3: devuelve los usuarios registrados sin modificarlos."""
        self._verificar_administrador(actor)
        return self._repositorio.listar()

    @staticmethod
    def _verificar_administrador(actor):
        if not actor.activo:
            raise UsuarioInactivoError()
        if actor.rol != Rol.ADMINISTRADOR:
            raise RolNoAutorizadoError()

    def _validar_rol(self, rol):
        if rol not in self.ROLES_ASIGNABLES:
            raise RolInvalidoError()

    def _validar_username_disponible(self, username):
        if self._repositorio.existe_username(username):
            raise UsuarioDuplicadoError()
