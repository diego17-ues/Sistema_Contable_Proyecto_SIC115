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


def desglosar_mano_obra(salario_bruto, parametros):
    """Calcula retenciones y cargas patronales desde mano de obra directa."""
    bruto = a_centavos(salario_bruto)
    base_isss = min(bruto, Decimal(parametros.isss_tope_mensual))
    isss_empleado = a_centavos(
        base_isss * Decimal(parametros.isss_empleado) / Decimal("100")
    )
    afp_empleado = a_centavos(
        bruto * Decimal(parametros.afp_empleado) / Decimal("100")
    )
    base_renta = max(bruto - isss_empleado - afp_empleado, CERO)
    renta = calcular_renta_mensual(base_renta, parametros)

    isss_patronal = a_centavos(
        base_isss * Decimal(parametros.isss_patronal) / Decimal("100")
    )
    afp_patronal = a_centavos(
        bruto * Decimal(parametros.afp_patronal) / Decimal("100")
    )
    incaf_patronal = a_centavos(
        bruto * Decimal(parametros.incaf_patronal) / Decimal("100")
    )
    cargas_patronales = a_centavos(
        isss_patronal + afp_patronal + incaf_patronal
    )
    retenciones = a_centavos(isss_empleado + afp_empleado + renta)
    return {
        "salario_bruto": bruto,
        "isss_empleado": isss_empleado,
        "afp_empleado": afp_empleado,
        "renta_retenida": renta,
        "isss_patronal": isss_patronal,
        "afp_patronal": afp_patronal,
        "incaf_patronal": incaf_patronal,
        "retenciones": retenciones,
        "cargas_patronales": cargas_patronales,
        "salario_neto": a_centavos(bruto - retenciones),
        "costo_total": a_centavos(bruto + cargas_patronales),
        "base_renta": base_renta,
    }


def calcular_renta_mensual(base, parametros):
    """Aplica la tabla mensual de retención parametrizada."""
    base = a_centavos(base)
    if base <= Decimal(parametros.renta_tramo_1_hasta):
        return a_centavos(0)

    if base <= Decimal(parametros.renta_tramo_2_hasta):
        porcentaje = Decimal(parametros.renta_tramo_2_porcentaje)
        exceso = Decimal(parametros.renta_tramo_2_exceso)
        cuota = Decimal(parametros.renta_tramo_2_cuota)
    elif base <= Decimal(parametros.renta_tramo_3_hasta):
        porcentaje = Decimal(parametros.renta_tramo_3_porcentaje)
        exceso = Decimal(parametros.renta_tramo_3_exceso)
        cuota = Decimal(parametros.renta_tramo_3_cuota)
    else:
        porcentaje = Decimal(parametros.renta_tramo_4_porcentaje)
        exceso = Decimal(parametros.renta_tramo_4_exceso)
        cuota = Decimal(parametros.renta_tramo_4_cuota)
    return a_centavos(
        cuota + (base - exceso) * porcentaje / Decimal("100")
    )


def lineas_mano_obra(cuenta_costo, cuenta_salarios, cuenta_retenciones,
                     cuenta_renta, cuenta_cargas, desglose):
    """Asiento de mano de obra, deducciones del trabajador y cargas."""
    lineas = [
        (cuenta_costo, desglose["costo_total"]),
        (cuenta_salarios, -desglose["salario_neto"]),
        (cuenta_retenciones, -a_centavos(
            desglose["isss_empleado"] + desglose["afp_empleado"]
        )),
        (cuenta_renta, -desglose["renta_retenida"]),
        (cuenta_cargas, -desglose["cargas_patronales"]),
    ]
    importes_por_cuenta = {}
    cuentas = {}
    for cuenta, importe in lineas:
        importes_por_cuenta[cuenta.pk] = (
            importes_por_cuenta.get(cuenta.pk, CERO) + importe
        )
        cuentas[cuenta.pk] = cuenta
    return [
        (cuentas[pk], a_centavos(importe))
        for pk, importe in importes_por_cuenta.items() if importe
    ]


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


def cuota_amortizacion(*, base, acumulado, vida_util_meses, modalidad,
                       desde, hasta):
    """Cuota de amortización lineal del tramo [desde, hasta].

    - DIARIA: base × días / días de vida útil (meses × 365 / 12).
    - MENSUAL: base × meses tocados por el tramo / vida útil en meses.
    - ANUAL: base × 12 / vida útil por cada 31/12 incluido en el tramo.
    Nunca supera el saldo pendiente (base − acumulado).
    """
    base, acumulado = Decimal(base), Decimal(acumulado or 0)
    pendiente = base - acumulado
    if desde > hasta or pendiente <= 0:
        return CERO
    vida = Decimal(vida_util_meses)
    if modalidad == "DIARIA":
        dias = Decimal((hasta - desde).days + 1)
        cuota = base * dias * 12 / (vida * 365)
    elif modalidad == "ANUAL":
        cierres = sum(
            1 for anio in range(desde.year, hasta.year + 1)
            if desde <= desde.replace(year=anio, month=12, day=31) <= hasta
        )
        cuota = base * 12 * cierres / vida
    else:
        meses = ((hasta.year - desde.year) * 12
                 + hasta.month - desde.month + 1)
        cuota = base * meses / vida
    return min(a_centavos(cuota), pendiente)
