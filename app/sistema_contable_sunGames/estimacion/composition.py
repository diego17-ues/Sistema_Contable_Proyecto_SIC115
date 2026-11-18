"""Punto único de composición de dependencias de la app de estimación."""

from django.db import transaction

from bitacora.services import BitacoraService
from bitacora.repositories import BitacoraRepository

from .repositories import EstimacionRepository
from .services import EstimacionService, PresupuestoService


def crear_bitacora_service():
    return BitacoraService(BitacoraRepository())


def _nueva_estimacion_service():
    return EstimacionService(
        EstimacionRepository(),
        crear_bitacora_service(),
        transaction.atomic,
    )


def crear_estimacion_service():
    return _nueva_estimacion_service()


def crear_presupuesto_service():
    return PresupuestoService(
        EstimacionRepository(),
        crear_bitacora_service(),
        _nueva_estimacion_service(),
        transaction.atomic,
    )
