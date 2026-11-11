"""Construcción de los estados financieros (NIC 1) a partir de saldos.

Cada saldo es la suma firmada del Libro Mayor (Debe positivo, Haber
negativo). Activos se presentan con su saldo; pasivos, patrimonio e
ingresos con el signo invertido; en resultados los costos y gastos quedan
negativos para que los subtotales se sumen directamente.
"""

from decimal import Decimal
from itertools import groupby

from . import clasificacion as c
from .models import TipoEstado

CERO = Decimal("0.00")
CENTAVO = Decimal("0.01")


def fila(clase, texto, importe=None, codigo=""):
    return {
        "clase": clase, "texto": texto, "codigo": codigo,
        "importe": None if importe is None else str(
            Decimal(importe).quantize(CENTAVO)
        ),
    }


def _encabezado(periodo, tipo, titulo, cubre):
    return {
        "tipo": tipo, "titulo": titulo, "cubre": cubre,
        "periodo": periodo.nombre,
        "desde": periodo.fecha_inicio.isoformat(),
        "hasta": periodo.fecha_fin.isoformat(),
    }


def resultado_del_ejercicio(saldos):
    return sum(
        (-cuenta.saldo for cuenta in saldos
         if cuenta.rubro.codigo in (c.EGRESOS, c.INGRESOS)),
        CERO,
    )


def _del_rubro(saldos, rubro):
    return [cuenta for cuenta in saldos if cuenta.rubro.codigo == rubro]


def _seccion_por_subtipo(filas, titulo, cuentas, signo):
    filas.append(fila("seccion", titulo))
    total = CERO
    for (_, nombre), grupo in groupby(
        cuentas, key=lambda cuenta: (cuenta.subtipo.prefijo,
                                     cuenta.subtipo.nombre),
    ):
        filas.append(fila("grupo", nombre))
        subtotal = CERO
        for cuenta in grupo:
            importe = signo * cuenta.saldo
            filas.append(fila("cuenta", cuenta.denominacion, importe,
                              cuenta.codigo))
            subtotal += importe
        filas.append(fila("subtotal", f"Total {nombre.lower()}", subtotal))
        total += subtotal
    filas.append(fila("total", f"TOTAL {titulo}", total))
    return total


def balance_general(periodo, saldos):
    """Saldos acumulados a la fecha de fin del período."""
    filas = []
    activo = _seccion_por_subtipo(
        filas, "ACTIVO", _del_rubro(saldos, c.ACTIVO), 1
    )
    pasivo = _seccion_por_subtipo(
        filas, "PASIVO", _del_rubro(saldos, c.PASIVO), -1
    )
    filas.append(fila("seccion", "PATRIMONIO"))
    patrimonio = CERO
    for cuenta in _del_rubro(saldos, c.PATRIMONIO):
        filas.append(fila("cuenta", cuenta.denominacion, -cuenta.saldo,
                          cuenta.codigo))
        patrimonio -= cuenta.saldo
    resultado = resultado_del_ejercicio(saldos)
    filas.append(fila("cuenta", "Utilidad (pérdida) del ejercicio",
                      resultado))
    patrimonio += resultado
    filas.append(fila("total", "TOTAL PATRIMONIO", patrimonio))
    filas.append(fila("resultado", "TOTAL PASIVO Y PATRIMONIO",
                      pasivo + patrimonio))
    diferencia = activo - (pasivo + patrimonio)
    return {
        **_encabezado(
            periodo, TipoEstado.BALANCE_GENERAL,
            "Estado de Situación Financiera (Balance General)",
            f"Al {periodo.fecha_fin:%d/%m/%Y}",
        ),
        "filas": filas,
        "cuadra": diferencia == 0,
        "diferencia": str(diferencia.quantize(CENTAVO)),
    }


def estado_resultados(periodo, saldos):
    """Por función, con los saldos del rango del período."""
    resultados = [
        cuenta for cuenta in saldos
        if cuenta.rubro.codigo in (c.EGRESOS, c.INGRESOS)
    ]

    def egresos(subtipo, excluir=frozenset()):
        return [
            cuenta for cuenta in resultados
            if cuenta.rubro.codigo == c.EGRESOS
            and cuenta.subtipo.prefijo == subtipo
            and cuenta.codigo not in excluir
        ]

    ingresos = _del_rubro(resultados, c.INGRESOS)
    especiales = c.INGRESOS_ORDINARIOS | c.INGRESOS_FINANCIEROS
    filas = []

    def bloque(titulo, cuentas, siempre=False):
        if not cuentas and not siempre:
            return CERO
        filas.append(fila("seccion", titulo))
        total = CERO
        for cuenta in cuentas:
            filas.append(fila("cuenta", cuenta.denominacion, -cuenta.saldo,
                              cuenta.codigo))
            total -= cuenta.saldo
        filas.append(fila("subtotal", f"Total {titulo.lower()}", total))
        return total

    bruta = bloque(
        "Ingresos de actividades ordinarias",
        [x for x in ingresos if x.codigo in c.INGRESOS_ORDINARIOS], True,
    ) + bloque("Costo de ventas", egresos(c.COSTO_VENTAS), True)
    filas.append(fila("total", "Utilidad (pérdida) bruta", bruta))
    operacion = bruta + bloque(
        "Gastos de administración", egresos(c.GASTOS_ADMINISTRACION)
    ) + bloque("Gastos de venta", egresos(c.GASTOS_VENTA))
    filas.append(fila("total", "Utilidad (pérdida) de operación", operacion))
    antes = operacion + sum((
        bloque("Ingresos financieros",
               [x for x in ingresos if x.codigo in c.INGRESOS_FINANCIEROS]),
        bloque("Gastos financieros", egresos(c.GASTOS_FINANCIEROS)),
        bloque("Otros ingresos",
               [x for x in ingresos if x.codigo not in especiales]),
        bloque("Otros gastos",
               egresos(c.OTROS_EGRESOS, excluir=c.IMPUESTO_RENTA)),
    ), CERO)
    filas.append(fila(
        "total", "Utilidad (pérdida) antes de impuesto sobre la renta", antes
    ))
    impuesto = bloque(
        "Impuesto sobre la renta",
        [x for x in resultados if x.codigo in c.IMPUESTO_RENTA],
    )
    filas.append(fila("resultado", "Utilidad (pérdida) del período",
                      antes + impuesto))
    return {
        **_encabezado(
            periodo, TipoEstado.ESTADO_RESULTADOS, "Estado de Resultados",
            f"Del {periodo.fecha_inicio:%d/%m/%Y} al "
            f"{periodo.fecha_fin:%d/%m/%Y}",
        ),
        "filas": filas,
    }
