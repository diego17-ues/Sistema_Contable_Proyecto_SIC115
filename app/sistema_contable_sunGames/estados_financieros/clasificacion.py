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
