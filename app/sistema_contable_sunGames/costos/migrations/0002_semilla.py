"""Datos semilla del módulo de costos.

- 4 procesos de desarrollo.
- Mapeo concepto → cuenta del catálogo real (4101, 4102, 4103, 1107).
- Parámetros laborales con vigencia; la tasa de cargas queda
  ``verificado=False`` (VERIFICAR, pendiente de confirmación).
"""

from decimal import Decimal

from django.db import migrations

PROCESOS = [
    ("Programación", "Mecánicas, UI, guardado, red y builds."),
    ("Arte y animación", "Personajes, escenarios y animación."),
    ("Audio", "Pistas, SFX y mezcla."),
    ("QA y accesibilidad", "Ciclos de pruebas, hardware y accesibilidad."),
]

# concepto → código de cuenta del catálogo (catalogo/migrations/0004).
MAPEOS = [
    ("mano_obra", "4101"),
    ("servicio_directo", "4102"),
    ("indirecto", "4103"),
    ("intangible", "1107"),
]

PARAMETROS = [
    ("horas_semana", Decimal("44"), "Horas semanales de la jornada."),
    ("semanas_año", Decimal("52"), "Semanas laborables al año."),
    ("tasa_cargas_patronales", Decimal("0.246"),
     "Tasa de cargas patronales sobre salario bruto (VERIFICAR)."),
]


def sembrar(apps, schema_editor):
    Proceso = apps.get_model("costos", "Proceso")
    MapeoCuenta = apps.get_model("costos", "MapeoCuenta")
    ParametroVigente = apps.get_model("costos", "ParametroVigente")
    Cuenta = apps.get_model("catalogo", "Cuenta")

    for nombre, descripcion in PROCESOS:
        Proceso.objects.get_or_create(
            nombre=nombre, defaults={"descripcion": descripcion}
        )
    for concepto, codigo in MAPEOS:
        cuenta = Cuenta.objects.filter(codigo=codigo).first()
        if cuenta is not None:
            MapeoCuenta.objects.get_or_create(
                concepto=concepto, defaults={"cuenta": cuenta}
            )
    for concepto, valor, descripcion in PARAMETROS:
        ParametroVigente.objects.get_or_create(
            concepto=concepto, vigente_desde="2020-01-01",
            defaults={
                "valor": valor, "verificado": False,
                "descripcion": descripcion,
            },
        )


def revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("costos", "0001_initial"),
        ("catalogo", "0004_catalogo_inicial"),
    ]

    operations = [
        migrations.RunPython(sembrar, revertir),
    ]
