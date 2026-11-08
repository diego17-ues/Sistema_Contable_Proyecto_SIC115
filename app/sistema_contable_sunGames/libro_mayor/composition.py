"""Punto único de composición de dependencias del Libro Mayor."""

from decimal import Decimal

from django.conf import settings
from django.db import transaction

from usuarios.composition import crear_bitacora_service

from .repositories import TransaccionRepository
from .services import ConfiguracionLibroMayor, LibroMayorService


def configuracion():
    valores = dict(getattr(settings, "LIBRO_MAYOR", {}))
    if valores.get("IMPORTE_MAXIMO") is not None:
        valores["IMPORTE_MAXIMO"] = Decimal(str(valores["IMPORTE_MAXIMO"]))
    return ConfiguracionLibroMayor(
        **{clave.lower(): valor for clave, valor in valores.items()}
    )


def crear_libro_mayor_service():
    return LibroMayorService(
        TransaccionRepository(), crear_bitacora_service(), configuracion(),
        transaction.atomic,
    )
