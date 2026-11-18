"""Fases fijas de desarrollo de SunGames (matriz de funciones).

Cada fase lleva su clasificación contable: CAPEX (capitalizable),
OPEX (gasto del período) o MIXTO según la regla de corte vigente.
"""

CLASIFICACION_CAPEX = "CAPEX"
CLASIFICACION_OPEX = "OPEX"
CLASIFICACION_MIXTO = "MIXTO"

FASES_SUN_GAMES = (
    ("Dirección de producto / productor", CLASIFICACION_MIXTO),
    ("Diseño de juego y narrativa", CLASIFICACION_CAPEX),
    ("Programación", CLASIFICACION_CAPEX),
    ("Arte y animación", CLASIFICACION_OPEX),
    ("Audio", CLASIFICACION_OPEX),
    ("QA y accesibilidad", CLASIFICACION_OPEX),
    ("Localización", CLASIFICACION_OPEX),
)
