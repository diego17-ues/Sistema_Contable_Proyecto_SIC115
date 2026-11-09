from django.db import migrations, models


def copiar_estado(apps, schema_editor):
    PeriodoContable = apps.get_model("libro_mayor", "PeriodoContable")
    PeriodoContable.objects.filter(cerrado=True).update(
        estado="CIERRE_PROVISIONAL"
    )


def copiar_cerrado(apps, schema_editor):
    PeriodoContable = apps.get_model("libro_mayor", "PeriodoContable")
    PeriodoContable.objects.exclude(estado="ABIERTO").update(cerrado=True)


class Migration(migrations.Migration):
    dependencies = [("libro_mayor", "0004_transaccion_solo_agrupa")]

    operations = [
        migrations.AddField(
            model_name="periodocontable",
            name="estado",
            field=models.CharField(
                choices=[("ABIERTO", "Abierto"),
                         ("CIERRE_PROVISIONAL", "Cierre provisional")],
                default="ABIERTO", max_length=20, verbose_name="estado",
            ),
        ),
        migrations.RunPython(copiar_estado, copiar_cerrado),
        migrations.RemoveField(model_name="periodocontable", name="cerrado"),
        migrations.AddConstraint(
            model_name="periodocontable",
            constraint=models.CheckConstraint(
                check=models.Q(estado__in=["ABIERTO", "CIERRE_PROVISIONAL"]),
                name="periodo_estado_valido",
            ),
        ),
    ]
