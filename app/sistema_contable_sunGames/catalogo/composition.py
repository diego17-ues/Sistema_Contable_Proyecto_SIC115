"""Punto único de composición de dependencias del catálogo."""

from django.db import transaction

from usuarios.composition import crear_bitacora_service

from .repositories import CuentaRepository
from .services import CatalogoCuentasService


def crear_catalogo_service():
    return CatalogoCuentasService(
        CuentaRepository(), crear_bitacora_service(), transaction.atomic
    )
