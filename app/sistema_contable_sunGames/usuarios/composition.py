"""Punto único de composición de dependencias de la app de usuarios."""

from bitacora.repositories import BitacoraRepository
from bitacora.services import BitacoraService

from .autenticacion import AutenticadorDjango
from .repositories import UsuarioRepository
from .services import AccesoService, AutenticacionService, UsuarioService


def crear_usuario_service():
    return UsuarioService(UsuarioRepository())


def crear_bitacora_service():
    return BitacoraService(BitacoraRepository())


def crear_autenticacion_service():
    return AutenticacionService(
        AutenticadorDjango(), UsuarioRepository(), crear_bitacora_service()
    )


def crear_acceso_service():
    return AccesoService()
