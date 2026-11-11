from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from catalogo.models import Cuenta

from .exceptions import MovimientoInvalidoError, PeriodoCerradoError

IMPORTE_MAX_DIGITS = 14
IMPORTE_DECIMALES = 2
CONCEPTO_MAX_LENGTH = 200
REFERENCIA_MAX_LENGTH = 40


class TipoMovimiento(models.TextChoices):
    DIARIO = "DIARIO", "Diario"
    COMPROBANTE_INGRESO = "COMPROBANTE_INGRESO", "Comprobante de Ingreso"
    COMPROBANTE_EGRESO = "COMPROBANTE_EGRESO", "Comprobante de Egreso"
    AJUSTE = "AJUSTE", "Ajuste"


class EstadoPeriodo(models.TextChoices):
    ABIERTO = "ABIERTO", "Abierto"
    # TODO(CU-07.3): el cierre anual definitivo (no reabrible) no está
    # definido; solo existe el cierre provisional.
    CIERRE_PROVISIONAL = "CIERRE_PROVISIONAL", "Cierre provisional"


class PeriodoContableQuerySet(models.QuerySet):
    def que_contienen(self, fecha):
        return self.filter(fecha_inicio__lte=fecha, fecha_fin__gte=fecha)

    def cerrado_en(self, fecha):
        return self.que_contienen(fecha).exclude(
            estado=EstadoPeriodo.ABIERTO
        ).exists()


class PeriodoContable(models.Model):
    """Rango de fechas del ejercicio y su estado. Fuente configurable.

    Un período cerrado no cambia de estado ni de datos salvo por la
    reapertura (CU-07), que guarda con ``save(reapertura=True)``.
    """

    nombre = models.CharField("nombre", max_length=40)
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_fin = models.DateField("fecha de fin")
    estado = models.CharField(
        "estado", max_length=20, choices=EstadoPeriodo.choices,
        default=EstadoPeriodo.ABIERTO,
    )

    objects = PeriodoContableQuerySet.as_manager()

    class Meta:
        ordering = ["fecha_inicio"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="periodo_rango_valido",
            ),
            models.CheckConstraint(
                check=models.Q(estado__in=EstadoPeriodo.values),
                name="periodo_estado_valido",
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def cerrado(self):
        return self.estado != EstadoPeriodo.ABIERTO

    def save(self, *args, reapertura=False, **kwargs):
        if self.pk and not reapertura and self._cerrado_en_base():
            raise PeriodoCerradoError(
                "El período está cerrado; solo la reapertura puede "
                "cambiarlo."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PeriodoCerradoError("Los períodos contables no se eliminan.")

    def _cerrado_en_base(self):
        anterior = type(self).objects.filter(pk=self.pk).values_list(
            "estado", flat=True
        ).first()
        return anterior is not None and anterior != EstadoPeriodo.ABIERTO


class Transaccion(models.Model):
    """Agrupa, para consulta, los movimientos guardados en un mismo envío."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="transacciones",
    )
    fecha_registro = models.DateTimeField(
        "fecha de registro", auto_now_add=True
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Transacción {self.pk}"


class MovimientoQuerySet(models.QuerySet):
    """Sin cambios en bloque: cada cambio pasa por ``Movimiento.save``."""

    def update(self, **kwargs):
        raise MovimientoInvalidoError(
            "Los movimientos del Libro Mayor no se modifican en bloque."
        )

    def delete(self):
        raise MovimientoInvalidoError(
            "Los movimientos del Libro Mayor no se eliminan."
        )


class Movimiento(models.Model):
    """Importe firmado: positivo es Debe (cargo), negativo es Haber (abono)."""

    transaccion = models.ForeignKey(
        Transaccion, on_delete=models.PROTECT, related_name="movimientos"
    )
    cuenta = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT, related_name="movimientos"
    )
    fecha = models.DateField("fecha")
    concepto = models.CharField("descripción", max_length=CONCEPTO_MAX_LENGTH)
    referencia = models.CharField(
        "referencia", max_length=REFERENCIA_MAX_LENGTH, blank=True
    )
    tipo = models.CharField(
        "tipo", max_length=20, choices=TipoMovimiento.choices
    )
    importe = models.DecimalField(
        "importe", max_digits=IMPORTE_MAX_DIGITS,
        decimal_places=IMPORTE_DECIMALES,
    )

    class Meta:
        ordering = ["fecha", "id"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(importe=0), name="movimiento_importe_no_cero"
            ),
        ]

    objects = MovimientoQuerySet.as_manager()

    def __str__(self):
        return f"{self.cuenta_id} {self.importe}"

    def clean(self):
        super().clean()
        try:
            self.verificar_periodo_abierto()
        except PeriodoCerradoError as exc:
            raise ValidationError({"fecha": str(exc)}) from exc

    def save(self, *args, **kwargs):
        self.verificar_periodo_abierto()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.verificar_periodo_abierto()
        raise MovimientoInvalidoError(
            "Los movimientos del Libro Mayor no se eliminan."
        )

    def verificar_periodo_abierto(self):
        """Ningún movimiento (ajustes incluidos) entra, cambia o sale de
        un período cerrado, venga de una vista, la consola o un comando."""
        fechas = {self.fecha}
        if self.pk:
            fechas.update(type(self).objects.filter(pk=self.pk).values_list(
                "fecha", flat=True
            ))
        for fecha in fechas:
            if fecha and PeriodoContable.objects.cerrado_en(fecha):
                raise PeriodoCerradoError(campo="fecha")
