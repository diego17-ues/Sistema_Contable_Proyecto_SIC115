from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('costos', '0008_cuentaindirectaexcluida_fuenteindirecta_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='ordentrabajo',
            name='eliminado_en',
            field=models.DateTimeField(blank=True, null=True,
                                       verbose_name='eliminado en'),
        ),
        migrations.AddField(
            model_name='ordentrabajo',
            name='eliminado_por',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='ordenes_eliminadas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='ordentrabajo',
            name='juego',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='ordenes_trabajo',
                to='costos.juego',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='ordentrabajo',
            name='orden_estimacion_ref_unica',
        ),
        migrations.AddConstraint(
            model_name='ordentrabajo',
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ('eliminado_en__isnull', True),
                    ('estimacion_ref__isnull', False),
                ),
                fields=('estimacion_ref',),
                name='orden_estimacion_ref_unica',
            ),
        ),
        migrations.AddConstraint(
            model_name='ordentrabajo',
            constraint=models.UniqueConstraint(
                condition=models.Q(('eliminado_en__isnull', True)),
                fields=('juego',),
                name='orden_activa_unica_por_juego',
            ),
        ),
        migrations.AddConstraint(
            model_name='ordentrabajo',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(('eliminado_en__isnull', True),
                             ('eliminado_por__isnull', True))
                    | models.Q(('eliminado_en__isnull', False),
                              ('eliminado_por__isnull', False))
                ),
                name='orden_baja_logica_completa',
            ),
        ),
    ]
