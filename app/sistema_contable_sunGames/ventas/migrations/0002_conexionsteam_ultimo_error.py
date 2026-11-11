from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0001_inicial"),
    ]

    operations = [
        migrations.AddField(
            model_name="conexionsteam",
            name="ultimo_error",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
