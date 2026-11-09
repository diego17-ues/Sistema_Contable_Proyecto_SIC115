import datetime

from django.db import migrations

# Supuesto (CU-05): no hay ejercicios definidos todavía; se carga el
# ejercicio 2026 abierto. Los cierres corresponden a CU-07.
EJERCICIO = {
    "nombre": "Ejercicio 2026",
    "fecha_inicio": datetime.date(2026, 1, 1),
    "fecha_fin": datetime.date(2026, 12, 31),
}


def cargar(apps, schema_editor):
    PeriodoContable = apps.get_model("libro_mayor", "PeriodoContable")
    PeriodoContable.objects.get_or_create(
        nombre=EJERCICIO["nombre"], defaults=EJERCICIO
    )


def quitar(apps, schema_editor):
    PeriodoContable = apps.get_model("libro_mayor", "PeriodoContable")
    PeriodoContable.objects.filter(nombre=EJERCICIO["nombre"]).delete()


class Migration(migrations.Migration):
    dependencies = [("libro_mayor", "0001_initial")]

    operations = [migrations.RunPython(cargar, quitar)]
