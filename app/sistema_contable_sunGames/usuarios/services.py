from bitacora.eventos import Accion, Resultado

from .exceptions import (
    AreaInicialPendienteError,
    CredencialesInvalidasError,
    CuentaNoHabilitadaError,
    RolInvalidoError,
    RolNoAutorizadoError,
    ServicioAutenticacionError,
    UsuarioDuplicadoError,
    UsuarioInactivoError,
    UsuarioNoEncontradoError,
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
        usuario = self._repositorio.nuevo(
            username=username, nombre_completo=nombre_completo, rol=rol
        )
        # TODO(CU-02.1): definir cómo se establece la contraseña de usuarios
        # nuevos (pendiente de definir en AGENTS.md). Mientras tanto la
        # cuenta se crea sin contraseña utilizable.
        usuario.set_unusable_password()
        # TODO(CU-03): registrar el alta en la bitácora mediante
        # BitacoraService, dentro de transaction.atomic().
        return self._repositorio.guardar(usuario)

    def desactivar(self, actor, username):
        """CU-02.2: cambia el estado a inactivo; el registro se conserva."""
        self._verificar_administrador(actor)
        usuario = self._repositorio.obtener_por_username(username)
        if not usuario.activo:
            raise UsuarioInactivoError("El usuario ya está inactivo.")
        # TODO(CU-03): registrar la desactivación en la bitácora mediante
        # BitacoraService, dentro de transaction.atomic().
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


class AutenticacionService:
    """CU-01 Iniciar sesión; cada intento se registra en la bitácora."""

    def __init__(self, autenticador, repositorio, bitacora):
        self._autenticador = autenticador
        self._repositorio = repositorio
        self._bitacora = bitacora

    def iniciar_sesion(self, request, username, password):
        usuario = self._verificar_credenciales(request, username, password)
        self._verificar_habilitado(usuario)
        self._abrir_sesion(request, usuario)
        self._registrar(Resultado.EXITOSO, usuario)
        return usuario

    def registrar_intento_incompleto(self, username):
        self._registrar(Resultado.DATOS_INCOMPLETOS, self._buscar(username))

    def _verificar_credenciales(self, request, username, password):
        try:
            return self._autenticador.verificar_credenciales(
                request, username, password
            )
        except CredencialesInvalidasError:
            self._registrar(
                Resultado.CREDENCIALES_INCORRECTAS, self._buscar(username)
            )
            raise
        except ServicioAutenticacionError:
            self._registrar_error_servicio(username)
            raise

    def _verificar_habilitado(self, usuario):
        if not usuario.activo:
            self._registrar(Resultado.CUENTA_NO_HABILITADA, usuario)
            raise CuentaNoHabilitadaError()

    def _abrir_sesion(self, request, usuario):
        try:
            self._autenticador.abrir_sesion(request, usuario)
        except ServicioAutenticacionError:
            self._registrar_error_servicio(usuario.username)
            raise

    def _registrar(self, resultado, actor):
        self._bitacora.registrar(Accion.INICIO_SESION, resultado, actor=actor)

    def _registrar_error_servicio(self, username):
        # La falla del servicio puede afectar también a la bitácora; el
        # error original debe informarse aunque el registro no se complete.
        try:
            self._registrar(Resultado.ERROR_SERVICIO, self._buscar(username))
        except Exception:  # noqa: BLE001
            pass

    def _buscar(self, username):
        if not username:
            return None
        try:
            return self._repositorio.obtener_por_username(username)
        except UsuarioNoEncontradoError:
            return None


class AccesoService:
    """Área inicial y módulos autorizados por rol (CU-01)."""

    AREA_INICIAL = {Rol.CONTADOR_GENERAL: "dashboard"}
    MODULOS = {
        Rol.CONTADOR_GENERAL: frozenset(
            {"dashboard", "ledger", "accounts", "reports", "operations"}
        ),
        # TODO(CU-01): el Administrador no tiene área inicial ni módulos
        # hasta que existan sus templates (CU-02, CU-03).
        Rol.ADMINISTRADOR: frozenset(),
    }

    def area_inicial(self, usuario):
        try:
            return self.AREA_INICIAL[usuario.rol]
        except KeyError as exc:
            raise AreaInicialPendienteError() from exc

    def verificar_acceso(self, usuario, modulo):
        if not usuario.activo:
            raise UsuarioInactivoError()
        if modulo not in self.MODULOS.get(usuario.rol, frozenset()):
            raise RolNoAutorizadoError()

    def modulos(self, usuario):
        return self.MODULOS.get(usuario.rol, frozenset())
