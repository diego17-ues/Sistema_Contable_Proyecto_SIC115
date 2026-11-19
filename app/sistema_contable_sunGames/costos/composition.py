"""Punto único de composición de dependencias del módulo de costos."""

from django.db import transaction

from estimacion.composition import crear_presupuesto_service
from libro_mayor.repositories import TransaccionRepository
from usuarios.composition import crear_bitacora_service

from .repositories import CostosRepository
from .services import (
    CatalogoCostosService,
    OrdenService,
    RegistroCostoService,
)


def _servicio(clase):
    return clase(CostosRepository(), crear_bitacora_service(),
                 transaction.atomic)


def crear_orden_service():
    return OrdenService(
        CostosRepository(), crear_bitacora_service(), transaction.atomic,
        total_estimacion=crear_presupuesto_service().total,
    )


def crear_registro_service():
    return RegistroCostoService(
        CostosRepository(), TransaccionRepository(),
        crear_bitacora_service(), transaction.atomic,
    )


def crear_catalogo_costos_service():
    return _servicio(CatalogoCostosService)
