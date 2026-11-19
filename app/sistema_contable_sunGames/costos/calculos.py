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


def distribuir_por_horas(pool, horas_por_orden):
    """Distribuye un pool proporcional a las horas de cada orden.

    Las órdenes se procesan por id y cualquier diferencia de centavos se
    asigna a la última, de modo que las asignaciones sumen exactamente el
    pool recibido.
    """
    pool = a_centavos(pool)
    horas_validas = {
        orden_id: Decimal(horas)
        for orden_id, horas in horas_por_orden.items()
        if Decimal(horas) > CERO
    }
    if pool <= CERO or not horas_validas:
        return {orden_id: CERO.quantize(CENTAVO)
                for orden_id in sorted(horas_validas)}

    ordenes = sorted(horas_validas)
    horas_totales = sum(horas_validas.values(), CERO)
    asignaciones = {}
    acumulado = CERO
    for orden_id in ordenes[:-1]:
        importe = a_centavos(
            pool * horas_validas[orden_id] / horas_totales
        )
        asignaciones[orden_id] = importe
        acumulado += importe
    asignaciones[ordenes[-1]] = a_centavos(pool - acumulado)
    return asignaciones


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


def comparar_estimado_real(total_estimado, total_real):
    """Compara los totales estimado y real; la variación es real − estimado.

    El porcentaje se expresa respecto del total estimado. No se calcula si
    el presupuesto estimado es cero.
    """
    total_estimado = a_centavos(total_estimado)
    total_real = a_centavos(total_real)
    variacion = a_centavos(total_real - total_estimado)
    porcentaje = None

    if total_estimado > CERO:
        porcentaje = (variacion * Decimal("100") / total_estimado).quantize(
            CENTAVO, rounding=ROUND_HALF_UP
        )

    if variacion > CERO:
        estado = "POR_ENCIMA"
    elif variacion < CERO:
        estado = "POR_DEBAJO"
    else:
        estado = "COINCIDE"

    return {
        "total_estimado": total_estimado,
        "total_real": total_real,
        "variacion": variacion,
        "variacion_abs": abs(variacion),
        "porcentaje": porcentaje,
        "estado": estado,
        "viable": total_real <= total_estimado,
    }


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
        if registro.elemento == "MANO_OBRA":
            fila["horas"] += registro.horas or CERO
    procesos = sorted(por_proceso.values(),
                      key=lambda f: (f["proceso"] is None, f["proceso"] or ""))
    return por_elemento, procesos, sum(por_elemento.values(), CERO)
