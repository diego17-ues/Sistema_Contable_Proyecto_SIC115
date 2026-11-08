from django.conf import settings
from django.db import models

from .eventos import Accion, Resultado


class RegistroBitacora(models.Model):
    fecha_hora = models.DateTimeField("fecha y hora", auto_now_add=True)
    # TODO(CU-01/CU-03): la especificación no define cómo identificar al
    # actor de un intento con un nombre de usuario inexistente; se registra
    # sin actor.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario actor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="acciones_bitacora",
    )
    afectado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario afectado",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="afectaciones_bitacora",
    )
    referencia = models.CharField(
        "registro afectado", max_length=60, blank=True, default=""
    )
    accion = models.CharField("acción", max_length=40, choices=Accion.choices)
    resultado = models.CharField(
        "resultado", max_length=40, choices=Resultado.choices
    )

    class Meta:
        verbose_name = "registro de bitácora"
        verbose_name_plural = "registros de bitácora"
        ordering = ["-fecha_hora", "-id"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(accion__in=Accion.values),
                name="bitacora_accion_valida",
            ),
            models.CheckConstraint(
                check=models.Q(resultado__in=Resultado.values),
                name="bitacora_resultado_valido",
            ),
        ]

    def __str__(self):
        return f"{self.accion} {self.resultado}"
