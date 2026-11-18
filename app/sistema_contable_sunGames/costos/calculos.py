"""Cálculos puros del costeo con Decimal. Sin ORM ni efectos."""

from decimal import Decimal, ROUND_DOWN

CENTAVO = Decimal("0.01")


def horas_mensuales(horas_semana, semanas_anio):
    """Horas mensuales = horas/semana × semanas/año ÷ 12.

    Con 44 × 52 / 12 = 190.6666… se conserva la fracción: la precisión se
    pierde solo al cuantizar importes, no las horas.
    """
    return Decimal(horas_semana) * Decimal(semanas_anio) / Decimal(12)


def costo_hora_pagada(salario_bruto, tasa_cargas, horas_mes):
    """Costo por hora pagada = salario × (1 + cargas) / horas mensuales."""
    return (Decimal(salario_bruto) * (Decimal(1) + Decimal(tasa_cargas))
            / Decimal(horas_mes))


def tasa_proceso(costo, horas_base):
    """Tasa por hora del proceso = costo del período / horas base."""
    costo = Decimal(costo)
    horas = Decimal(horas_base)
    if horas == 0:
        raise ValueError("horas_base no puede ser cero")
    return costo / horas


def cuota_depreciacion(costo, valor_residual, vida_util_meses):
    """Línea recta: (costo − residual) / vida útil en meses."""
    base = Decimal(costo) - Decimal(valor_residual)
    if base <= 0 or not vida_util_meses:
        return Decimal("0")
    return base / Decimal(vida_util_meses)


def repartir(monto, pesos):
    """Reparte ``monto`` entre partes proporcionales a ``pesos``.

    Todos los importes menos el último se cuantizan hacia abajo al
    centavo; el último absorbe el remanente para que la suma sea exacta.
    Requiere al menos una parte con peso positivo.
    """
    monto = Decimal(monto)
    pesos = [Decimal(p) for p in pesos]
    total = sum(pesos)
    if total <= 0:
        raise ValueError("La suma de pesos debe ser positiva.")
    if len(pesos) == 1:
        return [monto]
    cuotas = []
    acumulado = Decimal("0")
    for peso in pesos[:-1]:
        cuota = (monto * peso / total).quantize(
            CENTAVO, rounding=ROUND_DOWN
        )
        cuotas.append(cuota)
        acumulado += cuota
    cuotas.append(monto - acumulado)
    return cuotas


def aplicacion_proceso(tasa, horas_por_orden):
    """Aplica una tasa por hora a las horas de cada orden.

    Devuelve {orden_id: monto} con importes al centavo; la última orden
    absorbe el redondeo para conservar el total.
    """
    items = list(horas_por_orden.items())
    if not items:
        return {}
    bruto = [Decimal(horas) * Decimal(tasa) for _, horas in items]
    total_bruto = sum(bruto)
    # Cuantizar cada cuota; el remanente va a la última orden.
    cuotas = [b.quantize(CENTAVO, rounding=ROUND_DOWN) for b in bruto]
    remanente = (total_bruto - sum(cuotas)).quantize(CENTAVO)
    if remanente and items:
        cuotas[-1] += remanente
    return {orden_id: cuota for (orden_id, _), cuota in zip(items, cuotas)}
