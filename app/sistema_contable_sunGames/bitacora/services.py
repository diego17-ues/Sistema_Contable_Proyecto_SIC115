from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol

from .exceptions import GeneracionArchivoError, SinEventosError


class BitacoraService:
    """Registro de eventos de la bitácora (CU-03, solo escritura)."""

    def __init__(self, repositorio):
        self._repositorio = repositorio

    def registrar(self, accion, resultado, *, actor=None, afectado=None,
                  referencia="", detalle=""):
        extra = {"detalle": detalle} if detalle else {}
        return self._repositorio.crear(
            accion=accion, resultado=resultado, actor=actor,
            afectado=afectado, referencia=referencia, **extra,
        )


class AuditoriaService:
    """CU-03 Control de Auditoría: lectura y descarga de la bitácora."""

    def __init__(self, repositorio, fabrica_exportadores):
        self._repositorio = repositorio
        self._fabrica = fabrica_exportadores

    def listar(self, actor):
        """CU-03.1: devuelve los eventos sin modificarlos."""
        self._verificar_administrador(actor)
        return self._repositorio.listar()

    def exportar(self, actor, formato):
        """CU-03.2: genera el archivo con la estrategia del formato."""
        self._verificar_administrador(actor)
        exportador = self._fabrica.crear(formato)
        eventos = list(self._repositorio.listar())
        if not eventos:
            raise SinEventosError()
        try:
            return exportador.exportar(eventos)
        except Exception as exc:  # noqa: BLE001
            raise GeneracionArchivoError() from exc

    @staticmethod
    def _verificar_administrador(actor):
        if not actor.activo:
            raise UsuarioInactivoError()
        if actor.rol != Rol.ADMINISTRADOR:
            raise RolNoAutorizadoError()
