from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0002_conexionsteam_ultimo_error"),
    ]

    operations = [
        migrations.AddField(
            model_name="venta",
            name="origen",
            field=models.CharField(
                choices=[("REAL", "Real"), ("SIMULADA", "Simulada")],
                default="REAL",
                max_length=10,
                verbose_name="origen",
            ),
        ),
        migrations.AddConstraint(
            model_name="venta",
            constraint=models.CheckConstraint(
                check=models.Q(("origen__in", ["REAL", "SIMULADA"])),
                name="venta_origen_valido",
            ),
        ),
    ]
