from django.db import migrations, models


def copiar_de_transaccion(apps, schema_editor):
    Movimiento = apps.get_model("libro_mayor", "Movimiento")
    for movimiento in Movimiento.objects.select_related("transaccion"):
        movimiento.fecha = movimiento.transaccion.fecha
        movimiento.concepto = movimiento.transaccion.concepto
        movimiento.save(update_fields=["fecha", "concepto"])


def copiar_a_transaccion(apps, schema_editor):
    Movimiento = apps.get_model("libro_mayor", "Movimiento")
    for movimiento in Movimiento.objects.select_related("transaccion"):
        transaccion = movimiento.transaccion
        transaccion.fecha = movimiento.fecha
        transaccion.concepto = movimiento.concepto
        transaccion.save(update_fields=["fecha", "concepto"])


class Migration(migrations.Migration):
    dependencies = [("libro_mayor", "0002_ejercicio_2026")]

    operations = [
        migrations.RemoveConstraint(
            model_name="movimiento",
            name="movimiento_cuenta_unica_por_transaccion",
        ),
        migrations.AddField(
            model_name="movimiento",
            name="fecha",
            field=models.DateField(null=True, verbose_name="fecha"),
        ),
        migrations.AddField(
            model_name="movimiento",
            name="concepto",
            field=models.CharField(
                default="", max_length=200, verbose_name="descripción"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="movimiento",
            name="referencia",
            field=models.CharField(
                blank=True, default="", max_length=40,
                verbose_name="referencia",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="movimiento",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("DIARIO", "Diario"),
                    ("COMPROBANTE_INGRESO", "Comprobante de Ingreso"),
                    ("COMPROBANTE_EGRESO", "Comprobante de Egreso"),
                    ("AJUSTE", "Ajuste"),
                ],
                default="DIARIO", max_length=20, verbose_name="tipo",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(copiar_de_transaccion, copiar_a_transaccion),
    ]
