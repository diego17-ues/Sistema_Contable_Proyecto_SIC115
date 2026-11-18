"""Cálculos puros del subsistema de costos (sin ORM). Todo en Decimal."""

from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")


def a_centavos(valor):
    return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def importe_mano_obra(horas, costo_hora):
    """Importe = horas × costo por hora, redondeado a centavos."""
    return a_centavos(Decimal(horas) * Decimal(costo_hora))


def lineas_registro(cuenta_costo, contrapartida, importe):
    """Debe a la cuenta de costo y haber a la contrapartida (importe
    firmado: positivo = debe, negativo = haber)."""
    importe = a_centavos(importe)
    return [(cuenta_costo, importe), (contrapartida, -importe)]


def lineas_contrarias(lineas):
    return [(cuenta, -importe) for cuenta, importe in lineas]


def cuadra(lineas):
    return sum((importe for _, importe in lineas), Decimal("0")) == 0
