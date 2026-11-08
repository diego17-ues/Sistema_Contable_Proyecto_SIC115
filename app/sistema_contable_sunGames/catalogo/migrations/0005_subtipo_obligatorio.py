import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0004_catalogo_inicial")]

    operations = [
        migrations.AlterField(
            model_name="cuenta",
            name="subtipo",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="catalogo.subtipo",
            ),
        ),
    ]
