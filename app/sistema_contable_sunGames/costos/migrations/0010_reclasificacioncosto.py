from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("costos", "0009_orden_trabajo_baja_logica"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReclasificacionCosto",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "importe",
                    models.DecimalField(
                        decimal_places=2, max_digits=14,
                        validators=[MinValueValidator(0.01)],
                        verbose_name="importe",
                    ),
                ),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("CIERRE", "Cierre provisional"),
                            ("FINALIZACION", "Finalización de orden"),
                            ("REVERSION", "Reversión"),
                        ], max_length=16, verbose_name="tipo",
                    ),
                ),
                ("ciclo", models.PositiveIntegerField(default=1)),
                (
                    "clave_idempotencia",
                    models.CharField(
                        max_length=100, unique=True,
                        verbose_name="clave de idempotencia",
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "cuenta_destino",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reclasificaciones_costo_destino",
                        to="catalogo.cuenta",
                    ),
                ),
                (
                    "cuenta_origen",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reclasificaciones_costo_origen",
                        to="catalogo.cuenta",
                    ),
                ),
                (
                    "orden",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reclasificaciones_costos",
                        to="costos.ordentrabajo",
                    ),
                ),
                (
                    "origen",
                    models.ForeignKey(
                        blank=True,
                        help_text=(
                            "Reclasificación de cierre que originó el "
                            "saldo en 1106."
                        ),
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="derivadas",
                        to="costos.reclasificacioncosto",
                    ),
                ),
                (
                    "periodo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reclasificaciones_costos",
                        to="libro_mayor.periodocontable",
                    ),
                ),
                (
                    "revierte",
                    models.OneToOneField(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reversion",
                        to="costos.reclasificacioncosto",
                    ),
                ),
                (
                    "transaccion",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reclasificacion_costo",
                        to="libro_mayor.transaccion",
                    ),
                ),
            ],
            options={"ordering": ["id"]},
        ),
    ]
