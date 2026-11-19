"""Cálculos puros del subsistema de costos (sin ORM). Todo en Decimal."""

from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
DIEZMILESIMA = Decimal("0.0001")
CERO = Decimal("0")


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


def costo_unitario(total, licencias):
    """Costo total ÷ licencias estimadas a cuatro decimales; ``None``
    si no hay licencias."""
    if not licencias:
        return None
    return (Decimal(total) / Decimal(licencias)).quantize(
        DIEZMILESIMA, rounding=ROUND_HALF_UP
    )


def resumir(registros, elementos):
    """Totales de los registros vigentes por elemento y por proceso."""
    por_elemento = {elemento: CERO for elemento in elementos}
    por_proceso = {}
    for registro in registros:
        if not registro.vigente:
            continue
        por_elemento[registro.elemento] += registro.importe
        nombre = registro.proceso.nombre if registro.proceso else None
        fila = por_proceso.setdefault(
            nombre, {"proceso": nombre, "importe": CERO, "horas": CERO}
        )
        fila["importe"] += registro.importe
        fila["horas"] += registro.horas or CERO
    procesos = sorted(por_proceso.values(),
                      key=lambda f: (f["proceso"] is None, f["proceso"] or ""))
    return por_elemento, procesos, sum(por_elemento.values(), CERO)
