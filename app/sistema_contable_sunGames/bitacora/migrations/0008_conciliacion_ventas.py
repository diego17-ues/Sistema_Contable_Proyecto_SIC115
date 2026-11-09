from django.db import migrations, models


ACCIONES = [
    "INICIO_SESION",
    "ALTA_USUARIO",
    "DESACTIVACION_USUARIO",
    "REACTIVACION_USUARIO",
    "CAMBIO_CONTRASENA",
    "ALTA_CUENTA",
    "MODIFICACION_CUENTA",
    "REGISTRO_TRANSACCION",
    "CIERRE_PERIODO",
    "REAPERTURA_PERIODO",
    "EMISION_ESTADOS",
    "DESCARGA_ESTADO_PDF",
    "RECEPCION_VENTA",
    "CONTABILIZACION_VENTA",
    "CONCILIACION_VENTAS",
]

ETIQUETAS = [
    "Inicio de sesión",
    "Alta de usuario",
    "Desactivación de usuario",
    "Reactivación de usuario",
    "Cambio de contraseña",
    "Alta de cuenta",
    "Modificación de cuenta",
    "Registro de transacción",
    "Cierre de período",
    "Reapertura de período",
    "Emisión de estados financieros",
    "Descarga de estado financiero en PDF",
    "Recepción de venta Steam",
    "Contabilización de venta",
    "Conciliación de ventas Steam",
]


class Migration(migrations.Migration):

    dependencies = [
        ("bitacora", "0007_acciones_ventas"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="registrobitacora",
            name="bitacora_accion_valida",
        ),
        migrations.AlterField(
            model_name="registrobitacora",
            name="accion",
            field=models.CharField(
                choices=list(zip(ACCIONES, ETIQUETAS)), max_length=40,
                verbose_name="acción",
            ),
        ),
        migrations.AddConstraint(
            model_name="registrobitacora",
            constraint=models.CheckConstraint(
                check=models.Q(accion__in=ACCIONES),
                name="bitacora_accion_valida",
            ),
        ),
    ]
