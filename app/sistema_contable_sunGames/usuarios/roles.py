from django.db import models


class Rol(models.TextChoices):
    # El rol Contador de Costos está diferido (AGENT.md, "Alcance de la
    # entrega actual").
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
    CONTADOR_GENERAL = "CONTADOR_GENERAL", "Contador General"
