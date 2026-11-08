from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

CODIGO_LENGTH = 4
DENOMINACION_MAX_LENGTH = 150


class Rubro(models.Model):
    """Posición 1 del código de cuenta. Fuente configurable (CU-06)."""

    codigo = models.CharField(
        "código", max_length=1, unique=True,
        validators=[RegexValidator(r"^[0-9]$")],
    )
    nombre = models.CharField("nombre", max_length=80)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} {self.nombre}"


class Naturaleza(models.Model):
    """Posición 2 del código de cuenta. Fuente configurable (CU-06)."""

    codigo = models.CharField(
        "código", max_length=1, unique=True,
        validators=[RegexValidator(r"^[0-9]$")],
    )
    nombre = models.CharField("nombre", max_length=80)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} {self.nombre}"


class Grupo(models.Model):
    """Combinación válida de rubro y naturaleza (posiciones 1 y 2)."""

    rubro = models.ForeignKey(Rubro, on_delete=models.PROTECT)
    naturaleza = models.ForeignKey(Naturaleza, on_delete=models.PROTECT)

    class Meta:
        ordering = ["rubro__codigo", "naturaleza__codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["rubro", "naturaleza"], name="grupo_unico"
            ),
        ]

    def __str__(self):
        return f"{self.rubro.codigo}{self.naturaleza.codigo}"


class Cuenta(models.Model):
    codigo = models.CharField(
        "código", max_length=CODIGO_LENGTH, unique=True, editable=False
    )
    denominacion = models.CharField(
        "denominación", max_length=DENOMINACION_MAX_LENGTH
    )
    denominacion_normalizada = models.CharField(
        max_length=DENOMINACION_MAX_LENGTH, unique=True, editable=False
    )
    rubro = models.ForeignKey(Rubro, on_delete=models.PROTECT)
    naturaleza = models.ForeignKey(Naturaleza, on_delete=models.PROTECT)
    descripcion = models.TextField("descripción", blank=True)
    reglas_uso = models.TextField("reglas de uso", blank=True)
    activa = models.BooleanField("activa", default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["codigo"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(codigo__regex=r"^[0-9]{2}(0[1-9]|[1-9][0-9])$"),
                name="cuenta_codigo_cuatro_digitos",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} {self.denominacion}"


class AprobacionCuenta(models.Model):
    """Solicitud aprobada por Junta Directiva que respalda un alta o cambio."""

    class Tipo(models.TextChoices):
        ALTA = "ALTA", "Alta"
        MODIFICACION = "MODIFICACION", "Modificación"

    cuenta = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT, related_name="aprobaciones"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    justificacion = models.TextField("justificación")
    referencia_respaldo = models.CharField(
        "referencia de respaldo", max_length=150
    )
    acuerdo_numero = models.CharField("número de acuerdo", max_length=50)
    acuerdo_fecha = models.DateField("fecha de acuerdo")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="aprobaciones_cuentas",
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]


class HistorialCuenta(models.Model):
    """Valor anterior y nuevo de cada campo modificado (CU-06.3)."""

    aprobacion = models.ForeignKey(
        AprobacionCuenta, on_delete=models.PROTECT, related_name="cambios"
    )
    campo = models.CharField(max_length=30)
    valor_anterior = models.TextField(blank=True)
    valor_nuevo = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
