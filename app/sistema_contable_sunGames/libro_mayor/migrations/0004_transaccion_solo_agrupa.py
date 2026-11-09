from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("libro_mayor", "0003_movimiento_datos_propios")]

    operations = [
        migrations.AlterField(
            model_name="movimiento",
            name="fecha",
            field=models.DateField(verbose_name="fecha"),
        ),
        migrations.RemoveField(model_name="transaccion", name="fecha"),
        migrations.RemoveField(model_name="transaccion", name="concepto"),
        migrations.AlterModelOptions(
            name="transaccion", options={"ordering": ["id"]}
        ),
        migrations.AlterModelOptions(
            name="movimiento", options={"ordering": ["fecha", "id"]}
        ),
    ]
