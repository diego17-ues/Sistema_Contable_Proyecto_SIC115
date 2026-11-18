"""Cálculos puros del módulo de estimación. Todo en Decimal, sin float.

Ninguna función lee la base de datos ni escribe en el Libro Mayor: los
parámetros llegan ya resueltos por el servicio.
"""

from decimal import Decimal

MESES_POR_ANIO = Decimal("12")
PESO_MODA_PERT = Decimal("4")


def horas_mensuales(horas_semana, semanas_año):
    """Jornada mensual: horas_semana × semanas_año / 12."""
    return (horas_semana * semanas_año) / MESES_POR_ANIO


def costo_hora_pagada(salario_bruto, tasa_cargas_patronales, horas_mes):
    """Costo de una hora pagada con cargas patronales."""
    return (
        salario_bruto * (Decimal("1") + tasa_cargas_patronales)
    ) / horas_mes


def tarifa_efectiva(costo_hora_pagada, eficiencia):
    """Costo de una hora productiva estimada."""
    return costo_hora_pagada / eficiencia


def tarifa_rol(salario_bruto, tasa_cargas_patronales, horas_semana,
               semanas_año, eficiencia):
    """Cadena completa: salario bruto → tarifa efectiva del rol."""
    horas_mes = horas_mensuales(horas_semana, semanas_año)
    pagada = costo_hora_pagada(
        salario_bruto, tasa_cargas_patronales, horas_mes
    )
    return tarifa_efectiva(pagada, eficiencia)


def pert(optimista, moda, pesimista):
    """Distribución PERT: devuelve (E, sigma) en horas.

    E = (O + 4M + P) / 6 y sigma = (P − O) / 6.
    """
    esperado = (
        optimista + PESO_MODA_PERT * moda + pesimista
    ) / Decimal("6")
    sigma = (pesimista - optimista) / Decimal("6")
    return esperado, sigma


def costo_mano_obra(horas_E, tarifa):
    """Costo de mano de obra de una fase y rol: E × tarifa efectiva."""
    return horas_E * tarifa
