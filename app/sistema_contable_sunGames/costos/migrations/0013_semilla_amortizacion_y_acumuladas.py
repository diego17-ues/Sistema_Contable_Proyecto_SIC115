"""Parámetro inicial de amortización y contrapartidas acumuladas de CIF.

- Amortización de videojuegos: mensual, vida útil 48 meses (PREGUNTAS.md
  punto 7, por verificar); editable en Costos · Catálogos.
- Costos indirectos: se permiten como haber 1203 Depreciación acumulada y
  1205 Amortización acumulada de licencias, para registrar la depreciación
  del equipo y la amortización de licencias de desarrollo con un solo
  asiento (Debe 4103).
"""

from django.db import migrations

ACUMULADAS_CIF = ("1203", "1205")


def sembrar(apps, schema_editor):
    Parametro = apps.get_model("costos", "ParametroAmortizacion")
    if not Parametro.objects.exists():
        Parametro.objects.create(modalidad="MENSUAL", vida_util_meses=48)
    Config = apps.get_model("costos", "ConfiguracionCuentaCosto")
    Cuenta = apps.get_model("catalogo", "Cuenta")
    config = Config.objects.filter(elemento="INDIRECTO").first()
    if config is None:
        return
    config.contrapartidas.add(
        *Cuenta.objects.filter(codigo__in=ACUMULADAS_CIF, activa=True)
    )


class Migration(migrations.Migration):

    dependencies = [
        ("costos", "0012_amortizacion_videojuegos"),
    ]

    operations = [migrations.RunPython(sembrar, migrations.RunPython.noop)]
