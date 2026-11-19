from django.db import migrations, models


def crear_parametros(apps, schema_editor):
    parametros = apps.get_model("costos", "ParametrosCostosManoObra")
    parametros.objects.get_or_create(pk=1)


class Migration(migrations.Migration):

    dependencies = [
        ("costos", "0010_reclasificacioncosto"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParametrosCostosManoObra",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "isss_patronal",
                    models.DecimalField(
                        decimal_places=2, default="7.50", max_digits=5,
                        verbose_name="ISSS patronal (%)",
                    ),
                ),
                (
                    "isss_empleado",
                    models.DecimalField(
                        decimal_places=2, default="3.00", max_digits=5,
                        verbose_name="ISSS empleado (%)",
                    ),
                ),
                (
                    "isss_tope_mensual",
                    models.DecimalField(
                        decimal_places=2, default="1000.00", max_digits=10,
                        verbose_name="Base máxima mensual ISSS",
                    ),
                ),
                (
                    "afp_patronal",
                    models.DecimalField(
                        decimal_places=2, default="7.75", max_digits=5,
                        verbose_name="AFP patronal (%)",
                    ),
                ),
                (
                    "afp_empleado",
                    models.DecimalField(
                        decimal_places=2, default="7.25", max_digits=5,
                        verbose_name="AFP empleado (%)",
                    ),
                ),
                (
                    "incaf_patronal",
                    models.DecimalField(
                        decimal_places=2, default="1.00", max_digits=5,
                        verbose_name="INCAF patronal (%)",
                    ),
                ),
                (
                    "renta_tramo_1_hasta",
                    models.DecimalField(
                        decimal_places=2, default="550.00", max_digits=10,
                    ),
                ),
                (
                    "renta_tramo_2_hasta",
                    models.DecimalField(
                        decimal_places=2, default="895.24", max_digits=10,
                    ),
                ),
                (
                    "renta_tramo_2_porcentaje",
                    models.DecimalField(
                        decimal_places=2, default="10.00", max_digits=5,
                    ),
                ),
                (
                    "renta_tramo_2_exceso",
                    models.DecimalField(
                        decimal_places=2, default="550.00", max_digits=10,
                    ),
                ),
                (
                    "renta_tramo_2_cuota",
                    models.DecimalField(
                        decimal_places=2, default="17.67", max_digits=10,
                    ),
                ),
                (
                    "renta_tramo_3_hasta",
                    models.DecimalField(
                        decimal_places=2, default="2038.10", max_digits=10,
                    ),
                ),
                (
                    "renta_tramo_3_porcentaje",
                    models.DecimalField(
                        decimal_places=2, default="20.00", max_digits=5,
                    ),
                ),
                (
                    "renta_tramo_3_exceso",
                    models.DecimalField(
                        decimal_places=2, default="895.24", max_digits=10,
                    ),
                ),
                (
                    "renta_tramo_3_cuota",
                    models.DecimalField(
                        decimal_places=2, default="60.00", max_digits=10,
                    ),
                ),
                (
                    "renta_tramo_4_porcentaje",
                    models.DecimalField(
                        decimal_places=2, default="30.00", max_digits=5,
                    ),
                ),
                (
                    "renta_tramo_4_exceso",
                    models.DecimalField(
                        decimal_places=2, default="2038.10", max_digits=10,
                    ),
                ),
                (
                    "renta_tramo_4_cuota",
                    models.DecimalField(
                        decimal_places=2, default="288.57", max_digits=10,
                    ),
                ),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "parámetros de mano de obra",
                "verbose_name_plural": "parámetros de mano de obra",
            },
        ),
        migrations.RunPython(crear_parametros, migrations.RunPython.noop),
    ]
