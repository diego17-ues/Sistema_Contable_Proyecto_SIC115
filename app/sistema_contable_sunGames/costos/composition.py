"""Punto único de composición de dependencias del módulo de costos."""

from django.db import transaction

from usuarios.composition import crear_bitacora_service

from .repositories import CostosRepository
from .services import (
    CalculoService,
    CatalogoCostosService,
    OrdenService,
)


def _servicio(clase):
    return clase(CostosRepository(), crear_bitacora_service(),
                 transaction.atomic)


def crear_orden_service():
    return _servicio(OrdenService)


def crear_calculo_service():
    return _servicio(CalculoService)


def crear_catalogo_costos_service():
    return _servicio(CatalogoCostosService)
