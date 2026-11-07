from django.db import models


class Accion(models.TextChoices):
    INICIO_SESION = "INICIO_SESION", "Inicio de sesión"


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
