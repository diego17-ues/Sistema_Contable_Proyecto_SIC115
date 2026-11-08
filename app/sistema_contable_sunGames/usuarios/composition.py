"""Punto único de composición de dependencias de la app de usuarios."""

from django.db import transaction

from bitacora.exportadores import FabricaExportadores
from bitacora.repositories import BitacoraRepository
from bitacora.services import AuditoriaService, BitacoraService

from .autenticacion import AutenticadorDjango
from .repositories import UsuarioRepository
from .services import AccesoService, AutenticacionService, UsuarioService


def crear_usuario_service():
    return UsuarioService(
        UsuarioRepository(), crear_bitacora_service(), transaction.atomic
    )


def crear_auditoria_service():
    return AuditoriaService(BitacoraRepository(), FabricaExportadores())


def crear_bitacora_service():
    return BitacoraService(BitacoraRepository())


def crear_autenticacion_service():
    return AutenticacionService(
        AutenticadorDjango(), UsuarioRepository(), crear_bitacora_service()
    )


def crear_acceso_service():
    return AccesoService()
