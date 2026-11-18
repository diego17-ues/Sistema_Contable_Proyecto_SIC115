"""Semilla de la Etapa 1: procesos y configuración inicial de cuentas.

La configuración se toma del catálogo existente; si una cuenta no existe
o está inactiva el elemento queda sin configurar (bloqueado) y se
configura desde la pantalla de catálogos.
"""

from django.db import migrations
from django.db.models.functions import TruncDate

PROCESOS = ("Diseño", "Programación", "Arte", "Audio", "QA")
PROCESOS_ANTERIORES = ("Arte y animación", "QA y accesibilidad")

# elemento: (cuenta de costo, contrapartidas permitidas, por defecto)
CONFIGURACION = {
    "MANO_OBRA": ("4101", ("2106",), "2106"),
    "DIRECTO": ("4102", ("1103", "2101", "2102"), "2101"),
    "INDIRECTO": ("4103", ("1103", "2101", "2102", "1203"), "2102"),
}


def sembrar(apps, schema_editor):
    Proceso = apps.get_model("costos", "Proceso")
    Config = apps.get_model("costos", "ConfiguracionCuentaCosto")
    Cuenta = apps.get_model("catalogo", "Cuenta")
    OrdenTrabajo = apps.get_model("costos", "OrdenTrabajo")

    OrdenTrabajo.objects.update(fecha_inicio=TruncDate("fecha_creacion"))
    for nombre in PROCESOS:
        Proceso.objects.update_or_create(nombre=nombre,
                                         defaults={"activo": True})
    Proceso.objects.filter(nombre__in=PROCESOS_ANTERIORES).update(
        activo=False
    )

    cuentas = {c.codigo: c for c in Cuenta.objects.filter(activa=True)}
    for elemento, (debe, haberes, defecto) in CONFIGURACION.items():
        codigos = (debe, defecto, *haberes)
        if any(codigo not in cuentas for codigo in codigos):
            continue
        if Config.objects.filter(elemento=elemento).exists():
            continue
        config = Config.objects.create(
            elemento=elemento, cuenta_costo=cuentas[debe],
            contrapartida_defecto=cuentas[defecto],
        )
        config.contrapartidas.set([cuentas[c] for c in haberes])


def revertir(apps, schema_editor):
    apps.get_model("costos", "ConfiguracionCuentaCosto").objects.all().delete()
    Proceso = apps.get_model("costos", "Proceso")
    Proceso.objects.filter(nombre__in=PROCESOS_ANTERIORES).update(activo=True)


class Migration(migrations.Migration):

    dependencies = [
        ("costos", "0004_etapa1_registros_costo"),
        ("catalogo", "0005_subtipo_obligatorio"),
    ]

    operations = [migrations.RunPython(sembrar, revertir)]
