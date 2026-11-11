"""CU-07.2.1 Hoja de Trabajo calculada desde el Libro Mayor.

Conserva las columnas de la pantalla existente: balance de comprobación
(apertura + movimientos sin ajustes), ajustes, balance ajustado, estado de
resultados, cambios en el patrimonio y balance general. Los importes se
devuelven como texto decimal para transportarlos en JSON sin ``float``.
"""

from datetime import date
from decimal import Decimal

CERO = Decimal("0.00")
GRUPOS = {"1": "Activo", "2": "Pasivo", "3": "Patrimonio", "4": "Egreso",
          "5": "Ingreso"}
CLAVES = ("trialDebit", "trialCredit", "adjustDebit", "adjustCredit",
          "adjustedDebit", "adjustedCredit", "resultsDebit", "resultsCredit",
          "equityDebit", "equityCredit", "balanceDebit", "balanceCredit")


def _debe_haber(neto):
    return max(neto, CERO), max(-neto, CERO)


def _fila_cuenta(cuenta):
    grupo = GRUPOS.get(cuenta.rubro.codigo, "Orden")
    apertura = cuenta.apertura or CERO
    debe, haber = cuenta.debe or CERO, -(cuenta.haber or CERO)
    ajuste_debe, ajuste_haber = (cuenta.ajuste_debe or CERO,
                                 -(cuenta.ajuste_haber or CERO))
    comprobacion = apertura + debe - haber
    ajustado = comprobacion + ajuste_debe - ajuste_haber
    neto_periodo = debe + ajuste_debe - haber - ajuste_haber
    resultados = grupo in ("Ingreso", "Egreso")
    fila = {
        "code": cuenta.codigo, "name": cuenta.denominacion, "group": grupo,
        "nature": cuenta.naturaleza.nombre, "openingNet": apertura,
        "periodDebit": debe + ajuste_debe,
        "periodCredit": haber + ajuste_haber, "periodNet": neto_periodo,
        "adjustDebit": ajuste_debe, "adjustCredit": ajuste_haber,
    }
    fila["trialDebit"], fila["trialCredit"] = _debe_haber(comprobacion)
    fila["adjustedDebit"], fila["adjustedCredit"] = _debe_haber(ajustado)
    fila["resultsDebit"], fila["resultsCredit"] = (
        _debe_haber(neto_periodo) if resultados else (CERO, CERO)
    )
    patrimonio = grupo == "Patrimonio"
    balance = grupo in ("Activo", "Pasivo", "Patrimonio")
    for prefijo, incluir in (("equity", patrimonio), ("balance", balance)):
        fila[f"{prefijo}Debit"] = fila["adjustedDebit"] if incluir else CERO
        fila[f"{prefijo}Credit"] = fila["adjustedCredit"] if incluir else CERO
    return fila


def construir(desde, hasta, cuentas):
    filas = [_fila_cuenta(cuenta) for cuenta in cuentas]
    resultado = sum((f["periodNet"] for f in filas
                     if f["group"] in ("Ingreso", "Egreso")), CERO)
    if resultado:
        utilidad_debe, utilidad_haber = _debe_haber(resultado)
        filas.append({
            "code": "", "name": "Resultado del período", "group": "Resultado",
            **{clave: CERO for clave in CLAVES},
            "resultsDebit": utilidad_haber, "resultsCredit": utilidad_debe,
            "equityDebit": utilidad_debe, "equityCredit": utilidad_haber,
            "balanceDebit": utilidad_debe, "balanceCredit": utilidad_haber,
            "periodNet": -resultado, "openingNet": CERO,
            "periodDebit": CERO, "periodCredit": CERO,
        })
    totales = {clave: sum((f[clave] for f in filas), CERO)
               for clave in CLAVES}
    return {
        "from": desde.isoformat(), "to": hasta.isoformat(),
        "generatedAt": date.today().isoformat(),
        "rows": [_texto(f) for f in filas], "totals": _texto(totales),
    }


def _texto(datos):
    return {clave: str(valor) if isinstance(valor, Decimal) else valor
            for clave, valor in datos.items()}
