from django.db import migrations

# Elementos (posición 1) según el Manual de aplicación del catálogo de
# SunGames, sección 2.2.
# TODO(CU-06.1): el manual no asigna un dígito a cada naturaleza ni define
# grupos por naturaleza; Naturaleza y Grupo quedan vacíos hasta confirmarlos.
RUBROS = (
    ("1", "Activo"),
    ("2", "Pasivo"),
    ("3", "Patrimonio"),
    ("4", "Egresos"),
    ("5", "Ingresos"),
    ("6", "Cuentas de orden y de control deudoras"),
    ("7", "Cuentas de orden y de control acreedoras"),
)


def cargar_rubros(apps, schema_editor):
    Rubro = apps.get_model("catalogo", "Rubro")
    for codigo, nombre in RUBROS:
        Rubro.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})


def quitar_rubros(apps, schema_editor):
    Rubro = apps.get_model("catalogo", "Rubro")
    Rubro.objects.filter(
        codigo__in=[codigo for codigo, _ in RUBROS], cuenta__isnull=True
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0001_initial")]

    operations = [migrations.RunPython(cargar_rubros, quitar_rubros)]
