"""Punto único de composición de ventas."""

from django.conf import settings
from django.db import transaction

from libro_mayor.repositories import TransaccionRepository
from usuarios.composition import crear_bitacora_service

from .repositories import VentaRepository
from .services import ConfiguracionVentas, VentasService


def configuracion():
    valores = dict(getattr(settings, "VENTAS", {}))
    return ConfiguracionVentas(
        **{clave.lower(): valor for clave, valor in valores.items()}
    )


def token_steam():
    return getattr(settings, "STEAM_WEBHOOK_TOKEN", "")


def crear_ventas_service():
    return VentasService(
        VentaRepository(), TransaccionRepository(), crear_bitacora_service(),
        configuracion(), transaction.atomic,
    )
