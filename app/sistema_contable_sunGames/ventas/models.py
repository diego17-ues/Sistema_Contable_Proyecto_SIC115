from decimal import Decimal

from django.db import models
from django.utils import timezone

from libro_mayor.models import Transaccion

CENTAVO = Decimal("0.01")


class TipoProducto(models.TextChoices):
    JUEGO = "JUEGO", "Videojuego"
    DLC = "DLC", "Contenido adicional (DLC)"


class EstadoVenta(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    REGISTRADA = "REGISTRADA", "Registrada"


class Venta(models.Model):
    """Evento de venta recibido del servicio Steam simulado (CU-08.4)."""

    identificador = models.CharField(
        "identificador", max_length=64, unique=True
    )
    titulo = models.CharField("título", max_length=120)
    tipo_producto = models.CharField(
        "tipo de producto", max_length=10, choices=TipoProducto.choices
    )
    cantidad = models.PositiveIntegerField("cantidad")
    precio_unitario = models.DecimalField(
        "precio unitario", max_digits=12, decimal_places=2
    )
    moneda = models.CharField("moneda", max_length=3)
    pais = models.CharField("país", max_length=2)
    fecha_hora = models.DateTimeField("fecha y hora del evento")
    comision = models.DecimalField("comisión", max_digits=14,
                                   decimal_places=2)
    impuesto = models.DecimalField("impuesto", max_digits=14,
                                   decimal_places=2, default=Decimal("0"))
    estado = models.CharField(
        "estado", max_length=12, choices=EstadoVenta.choices,
        default=EstadoVenta.PENDIENTE,
    )
    transaccion = models.OneToOneField(
        Transaccion, on_delete=models.PROTECT, null=True, blank=True,
        related_name="venta",
    )
    fecha_recepcion = models.DateTimeField("recibida", auto_now_add=True)

    class Meta:
        ordering = ["-fecha_hora", "-id"]
        constraints = [
            models.CheckConstraint(check=models.Q(cantidad__gt=0),
                                   name="venta_cantidad_positiva"),
            models.CheckConstraint(check=models.Q(precio_unitario__gt=0),
                                   name="venta_precio_positivo"),
            models.CheckConstraint(check=models.Q(comision__gte=0),
                                   name="venta_comision_no_negativa"),
            models.CheckConstraint(check=models.Q(impuesto__gte=0),
                                   name="venta_impuesto_no_negativo"),
            models.CheckConstraint(
                check=models.Q(estado__in=EstadoVenta.values),
                name="venta_estado_valido",
            ),
            models.CheckConstraint(
                check=models.Q(tipo_producto__in=TipoProducto.values),
                name="venta_tipo_producto_valido",
            ),
        ]

    def __str__(self):
        return self.identificador

    @property
    def total(self):
        return (self.precio_unitario * self.cantidad).quantize(CENTAVO)

    @property
    def neto(self):
        return self.total - self.comision

    @property
    def fecha(self):
        return timezone.localdate(self.fecha_hora)


class ConexionSteam(models.Model):
    """Último contacto del servicio Steam simulado (un único registro)."""

    ultimo_contacto = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "conexión Steam"
