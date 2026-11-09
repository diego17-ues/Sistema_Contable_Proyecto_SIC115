from django.conf import settings
from django.db import models

from libro_mayor.models import PeriodoContable

from .exceptions import EstadoInmutableError


class TipoEstado(models.TextChoices):
    BALANCE_GENERAL = (
        "BALANCE_GENERAL", "Estado de Situación Financiera (Balance General)"
    )
    ESTADO_RESULTADOS = "ESTADO_RESULTADOS", "Estado de Resultados"


class EstadoEmitidoQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise EstadoInmutableError()

    def delete(self):
        raise EstadoInmutableError()


class EstadoFinancieroEmitido(models.Model):
    """Snapshot inmutable del estado financiero emitido al cerrar un
    período. ``datos`` guarda las filas ya calculadas (importes como texto
    decimal) para exportarlas sin recalcular."""

    periodo = models.ForeignKey(
        PeriodoContable, on_delete=models.PROTECT,
        related_name="estados_emitidos",
    )
    tipo = models.CharField(
        "estado", max_length=30, choices=TipoEstado.choices
    )
    datos = models.JSONField("datos")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="estados_emitidos",
    )
    fecha_emision = models.DateTimeField("fecha de emisión", auto_now_add=True)

    objects = EstadoEmitidoQuerySet.as_manager()

    class Meta:
        verbose_name = "estado financiero emitido"
        verbose_name_plural = "estados financieros emitidos"
        ordering = ["-fecha_emision", "-id"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(tipo__in=TipoEstado.values),
                name="estado_emitido_tipo_valido",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.periodo}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise EstadoInmutableError()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise EstadoInmutableError()
