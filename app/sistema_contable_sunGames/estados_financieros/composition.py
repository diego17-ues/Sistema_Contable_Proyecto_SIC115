"""Punto único de composición de estados financieros y cierres."""

from django.contrib.staticfiles import finders
from django.db import transaction

from libro_mayor.composition import LOGO
from usuarios.composition import crear_bitacora_service

from .exportadores import ExportadorEstadoPDF
from .repositories import EstadosFinancierosRepository
from .services import CierrePeriodoService, EstadosFinancierosService


def crear_estados_financieros_service():
    return EstadosFinancierosService(
        EstadosFinancierosRepository(), crear_bitacora_service(),
        ExportadorEstadoPDF(finders.find(LOGO)),
    )


def crear_cierre_service():
    return CierrePeriodoService(
        EstadosFinancierosRepository(), crear_estados_financieros_service(),
        crear_bitacora_service(), transaction.atomic,
    )
