"""Parámetro inicial de amortización de videojuegos terminados.

Mensual, vida útil 48 meses (PREGUNTAS.md punto 7, por verificar);
editable en Costos · Catálogos.
"""

from django.db import migrations


def sembrar(apps, schema_editor):
    Parametro = apps.get_model("costos", "ParametroAmortizacion")
    if not Parametro.objects.exists():
        Parametro.objects.create(modalidad="MENSUAL", vida_util_meses=48)


class Migration(migrations.Migration):

    dependencies = [
        ("costos", "0013_amortizacion_videojuegos"),
    ]

    operations = [migrations.RunPython(sembrar, migrations.RunPython.noop)]
