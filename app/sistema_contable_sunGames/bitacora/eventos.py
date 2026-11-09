from django.db import models


class Accion(models.TextChoices):
    INICIO_SESION = "INICIO_SESION", "Inicio de sesión"
    ALTA_USUARIO = "ALTA_USUARIO", "Alta de usuario"
    DESACTIVACION_USUARIO = "DESACTIVACION_USUARIO", "Desactivación de usuario"
    REACTIVACION_USUARIO = "REACTIVACION_USUARIO", "Reactivación de usuario"
    CAMBIO_CONTRASENA = "CAMBIO_CONTRASENA", "Cambio de contraseña"
    ALTA_CUENTA = "ALTA_CUENTA", "Alta de cuenta"
    MODIFICACION_CUENTA = "MODIFICACION_CUENTA", "Modificación de cuenta"
    REGISTRO_TRANSACCION = "REGISTRO_TRANSACCION", "Registro de transacción"


class Resultado(models.TextChoices):
    EXITOSO = "EXITOSO", "Exitoso"
    CREDENCIALES_INCORRECTAS = (
        "CREDENCIALES_INCORRECTAS", "Fallido: credenciales incorrectas"
    )
    DATOS_INCOMPLETOS = "DATOS_INCOMPLETOS", "Fallido: datos incompletos"
    ERROR_SERVICIO = (
        "ERROR_SERVICIO", "Fallido: error del servicio de autenticación"
    )
    CUENTA_NO_HABILITADA = (
        "CUENTA_NO_HABILITADA", "Rechazado: cuenta no habilitada"
    )
