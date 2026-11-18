from django.db import models


class Rol(models.TextChoices):
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
    CONTADOR_GENERAL = "CONTADOR_GENERAL", "Contador General"
    CONTADOR_COSTOS = "CONTADOR_COSTOS", "Contador de Costos"
