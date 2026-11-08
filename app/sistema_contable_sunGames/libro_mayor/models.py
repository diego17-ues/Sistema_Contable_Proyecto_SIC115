from django.conf import settings
from django.db import models

from catalogo.models import Cuenta

IMPORTE_MAX_DIGITS = 14
IMPORTE_DECIMALES = 2
CONCEPTO_MAX_LENGTH = 200


class PeriodoContable(models.Model):
    """Rango de fechas del ejercicio y su estado. Fuente configurable."""

    nombre = models.CharField("nombre", max_length=40)
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_fin = models.DateField("fecha de fin")
    cerrado = models.BooleanField("cerrado", default=False)

    class Meta:
        ordering = ["fecha_inicio"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="periodo_rango_valido",
            ),
        ]

    def __str__(self):
        return self.nombre


class Transaccion(models.Model):
    fecha = models.DateField("fecha")
    concepto = models.CharField("concepto", max_length=CONCEPTO_MAX_LENGTH)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="transacciones",
    )
    fecha_registro = models.DateTimeField(
        "fecha de registro", auto_now_add=True
    )

    class Meta:
        ordering = ["fecha", "id"]

    def __str__(self):
        return f"Transacción {self.pk}"


class Movimiento(models.Model):
    """Importe firmado: positivo carga la cuenta, negativo la abona."""

    transaccion = models.ForeignKey(
        Transaccion, on_delete=models.PROTECT, related_name="movimientos"
    )
    cuenta = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT, related_name="movimientos"
    )
    importe = models.DecimalField(
        "importe", max_digits=IMPORTE_MAX_DIGITS,
        decimal_places=IMPORTE_DECIMALES,
    )

    class Meta:
        ordering = ["transaccion__fecha", "transaccion_id", "id"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(importe=0), name="movimiento_importe_no_cero"
            ),
            models.UniqueConstraint(
                fields=["transaccion", "cuenta"],
                name="movimiento_cuenta_unica_por_transaccion",
            ),
        ]
