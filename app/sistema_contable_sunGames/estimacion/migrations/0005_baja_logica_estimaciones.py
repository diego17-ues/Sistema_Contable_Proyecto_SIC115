from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('estimacion', '0004_costofabricacion_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='estimacionexperto',
            name='eliminado_en',
            field=models.DateTimeField(blank=True, null=True,
                                       verbose_name='eliminado en'),
        ),
        migrations.AddField(
            model_name='estimacionexperto',
            name='eliminado_por',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='estimaciones_experto_eliminadas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='estimacionexperto',
            name='estimacion_unica_por_ronda',
        ),
        migrations.AddConstraint(
            model_name='estimacionexperto',
            constraint=models.UniqueConstraint(
                condition=models.Q(('eliminado_en__isnull', True)),
                fields=('juego', 'fase', 'rol', 'experto', 'ronda'),
                name='estimacion_unica_por_ronda',
            ),
        ),
        migrations.AddConstraint(
            model_name='estimacionexperto',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(('eliminado_en__isnull', True),
                             ('eliminado_por__isnull', True))
                    | models.Q(('eliminado_en__isnull', False),
                              ('eliminado_por__isnull', False))
                ),
                name='estimacion_baja_logica_completa',
            ),
        ),
        migrations.AddField(
            model_name='versionpresupuesto',
            name='eliminado_en',
            field=models.DateTimeField(blank=True, null=True,
                                       verbose_name='eliminado en'),
        ),
        migrations.AddField(
            model_name='versionpresupuesto',
            name='eliminado_por',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='versiones_presupuesto_eliminadas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name='versionpresupuesto',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(('eliminado_en__isnull', True),
                             ('eliminado_por__isnull', True))
                    | models.Q(('eliminado_en__isnull', False),
                              ('eliminado_por__isnull', False))
                ),
                name='version_baja_logica_completa',
            ),
        ),
    ]
