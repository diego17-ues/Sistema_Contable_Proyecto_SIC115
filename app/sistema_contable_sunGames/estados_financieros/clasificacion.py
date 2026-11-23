"""Clasificación NIC 1 sobre el catálogo de SunGames (CU-07.5, CU-07.6).

Supuesto documentado en el PR: el Balance General agrupa por los subtipos
del catálogo (11/21 corriente, 12/22 no corriente) y el Estado de
Resultados se presenta por función según los subtipos de egresos (41
costos, 42 administración, 43 venta, 44 financieros, 45 otros). Las
cuentas de orden (rubros 6 y 7) no forman parte de los estados.
"""

ACTIVO = "1"
PASIVO = "2"
PATRIMONIO = "3"
EGRESOS = "4"
INGRESOS = "5"

INGRESOS_ORDINARIOS = frozenset({"5101", "5102", "5103"})
INGRESOS_FINANCIEROS = frozenset({"5104"})
IMPUESTO_RENTA = frozenset({"4503"})

COSTO_VENTAS = "41"
GASTOS_ADMINISTRACION = "42"
GASTOS_VENTA = "43"
GASTOS_FINANCIEROS = "44"
OTROS_EGRESOS = "45"

# Costo de ventas: solo la amortización de videojuegos terminados (4104).
# El resto de la serie 41 (4101 mano de obra, 4102 directos, 4103 CIF) es
# costo de desarrollo capitalizable: no es gasto del período y, mientras
# no se traslade a 1106/1107, se presenta en el activo.
COSTO_VENTAS_CUENTAS = frozenset({"4104"})

# Cuentas acumuladas cuyo abono del período es depreciación/amortización.
DEPRECIACION_AMORTIZACION = (
    ("1108", "Amortización de videojuegos (costo de ventas)"),
    ("1203", "Depreciación de mobiliario y equipo"),
    ("1205", "Amortización de licencias de software"),
)


def es_costo_desarrollo(cuenta):
    """Serie 41 capitalizable (no entra al Estado de Resultados)."""
    return (cuenta.rubro.codigo == EGRESOS
            and cuenta.subtipo.prefijo == COSTO_VENTAS
            and cuenta.codigo not in COSTO_VENTAS_CUENTAS)


def es_resultado(cuenta):
    return (cuenta.rubro.codigo in (EGRESOS, INGRESOS)
            and not es_costo_desarrollo(cuenta))
