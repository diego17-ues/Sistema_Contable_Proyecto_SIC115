"""Datos semilla de parámetros con vigencia del módulo de estimación.

Los valores viven en la tabla `ParametroVigente`, no en el código.
`tasa_cargas_patronales` queda sin verificar (AFP pendiente con el
contador) y `umbral_dispersion_delphi` queda como DEFAULT para revisión.
"""

from datetime import date

from django.db import migrations

VIGENTE_DESDE = date(2026, 1, 1)

PARAMETROS = [
    ("horas_semana", "44", True),
    ("semanas_año", "52", True),
    ("tasa_cargas_patronales", "0.246", False),
    ("eficiencia", "0.85", True),
    ("umbral_dispersion_delphi", "0.20", False),
]


def sembrar_parametros(apps, schema_editor):
    ParametroVigente = apps.get_model("estimacion", "ParametroVigente")
    for clave, valor, verificado in PARAMETROS:
        existe = ParametroVigente.objects.filter(clave=clave).exists()
        if not existe:
            ParametroVigente.objects.create(
                clave=clave, valor=valor,
                vigente_desde=VIGENTE_DESDE, verificado=verificado,
            )


def retirar_parametros(apps, schema_editor):
    ParametroVigente = apps.get_model("estimacion", "ParametroVigente")
    ParametroVigente.objects.filter(
        clave__in=[clave for clave, _, _ in PARAMETROS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("estimacion", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sembrar_parametros, retirar_parametros),
    ]
