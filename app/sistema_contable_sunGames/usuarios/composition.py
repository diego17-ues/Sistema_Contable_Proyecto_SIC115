"""Punto único de composición de dependencias de la app de usuarios."""

from .repositories import UsuarioRepository
from .services import UsuarioService


def crear_usuario_service():
    return UsuarioService(UsuarioRepository())
