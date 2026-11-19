"""Modelos del subsistema de costos: órdenes de trabajo (Etapa 1).

Los registros de costo generan su asiento en el Libro Mayor por el
mecanismo de la contabilidad general (``TransaccionRepository``); este
módulo nunca escribe directo en las tablas del mayor. Aquí se guarda el
origen de cada asiento y su clave de idempotencia.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from catalogo.models import Cuenta
from estimacion.models import VersionPresupuesto
from libro_mayor.models import Transaccion

DINERO_MAX = 14
HORAS_MAX = 10


class Elemento(models.TextChoices):
    MANO_OBRA = "MANO_OBRA", "Mano de obra directa"
    DIRECTO = "DIRECTO", "Costo directo"
    INDIRECTO = "INDIRECTO", "Costo indirecto"


class Juego(models.Model):
    nombre = models.CharField("nombre", max_length=160, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class OrdenTrabajo(models.Model):
    """Una orden de trabajo por juego."""

    ESTADO_ABIERTA = "ABIERTA"
    ESTADO_CERRADA = "CERRADA"
    ESTADOS = [
        (ESTADO_ABIERTA, "Abierta"),
        (ESTADO_CERRADA, "Cerrada"),
    ]

    juego = models.OneToOneField(
        Juego, on_delete=models.PROTECT, related_name="orden"
    )
    estado = models.CharField(
        "estado", max_length=10, choices=ESTADOS, default=ESTADO_ABIERTA
    )
    fecha_inicio = models.DateField(
        "fecha de inicio", default=timezone.localdate
    )
    licencias_estimadas = models.PositiveIntegerField(
        "licencias estimadas", null=True, blank=True,
        validators=[MinValueValidator(1)],
    )
    estimacion_ref = models.ForeignKey(
        VersionPresupuesto, on_delete=models.PROTECT, null=True,
        blank=True, related_name="ordenes_trabajo",
        verbose_name="estimación de referencia",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="ordenes_creadas", null=True, blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(licencias_estimadas__isnull=True)
                | models.Q(licencias_estimadas__gt=0),
                name="orden_licencias_positivas",
            ),
        ]

    def __str__(self):
        return f"OT {self.pk} · {self.juego}"

    @property
    def abierta(self):
        return self.estado == self.ESTADO_ABIERTA


class Proceso(models.Model):
    """Catálogo configurable de procesos de desarrollo.

    ``costo_hora`` es el costo por hora que se propone al registrar mano
    de obra; se configura en la pantalla de catálogos, no en el código.
    """

    nombre = models.CharField("nombre", max_length=120, unique=True)
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    costo_hora = models.DecimalField(
        "costo por hora propuesto", max_digits=12, decimal_places=4,
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ConfiguracionCuentaCosto(models.Model):
    """Cuentas del catálogo por elemento del costo.

    Cuenta de costo (debe), contrapartidas permitidas (haber) y la
    contrapartida por defecto. Sin configuración el elemento queda
    bloqueado.
    """

    elemento = models.CharField(
        "elemento", max_length=12, choices=Elemento.choices, unique=True
    )
    cuenta_costo = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT, related_name="config_costo_debe"
    )
    contrapartidas = models.ManyToManyField(
        Cuenta, related_name="config_costo_haber",
        verbose_name="contrapartidas permitidas",
    )
    contrapartida_defecto = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT,
        related_name="config_costo_defecto",
    )

    class Meta:
        ordering = ["elemento"]

    def __str__(self):
        return f"{self.get_elemento_display()} → {self.cuenta_costo.codigo}"


class RegistroCosto(models.Model):
    """Registro de un elemento del costo en una orden.

    No se edita ni se borra: se anula y la anulación genera el
    contra-asiento.
    """

    ESTADO_VIGENTE = "VIGENTE"
    ESTADO_ANULADO = "ANULADO"
    ESTADOS = [
        (ESTADO_VIGENTE, "Vigente"),
        (ESTADO_ANULADO, "Anulado"),
    ]

    orden = models.ForeignKey(
        OrdenTrabajo, on_delete=models.PROTECT, related_name="registros"
    )
    elemento = models.CharField(
        "elemento", max_length=12, choices=Elemento.choices
    )
    fecha = models.DateField("fecha")
    proceso = models.ForeignKey(
        Proceso, on_delete=models.PROTECT, null=True, blank=True,
        related_name="registros",
    )
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    horas = models.DecimalField(
        "horas", max_digits=HORAS_MAX, decimal_places=2,
        null=True, blank=True,
    )
    costo_hora = models.DecimalField(
        "costo por hora", max_digits=12, decimal_places=4,
        null=True, blank=True,
    )
    importe = models.DecimalField(
        "importe", max_digits=DINERO_MAX, decimal_places=2
    )
    cuenta_costo = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT, related_name="registros_costo_debe"
    )
    contrapartida = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT,
        related_name="registros_costo_haber",
    )
    estado = models.CharField(
        "estado", max_length=10, choices=ESTADOS, default=ESTADO_VIGENTE
    )
    motivo_anulacion = models.CharField(
        "motivo de anulación", max_length=200, blank=True
    )
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="registros_costo_anulados", null=True, blank=True,
    )
    anulado_en = models.DateTimeField("anulado en", null=True, blank=True)
    clave_idempotencia = models.CharField(
        "clave de idempotencia", max_length=80, unique=True
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="registros_costo",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "id"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(importe__gt=0),
                name="registro_costo_importe_positivo",
            ),
            models.CheckConstraint(
                check=models.Q(estado__in=["VIGENTE", "ANULADO"]),
                name="registro_costo_estado_valido",
            ),
            models.CheckConstraint(
                check=~models.Q(elemento="MANO_OBRA") | models.Q(
                    proceso__isnull=False, horas__gt=0,
                    costo_hora__gt=0,
                ),
                name="registro_costo_mano_obra_completa",
            ),
        ]

    def __str__(self):
        return (f"{self.get_elemento_display()} ${self.importe} · "
                f"OT {self.orden_id}")

    @property
    def vigente(self):
        return self.estado == self.ESTADO_VIGENTE


class AsientoCosto(models.Model):
    """Origen de cada asiento del mayor generado por el módulo."""

    TIPO_REGISTRO = "REGISTRO"
    TIPO_ANULACION = "ANULACION"
    TIPOS = [
        (TIPO_REGISTRO, "Registro"),
        (TIPO_ANULACION, "Anulación"),
    ]

    transaccion = models.OneToOneField(
        Transaccion, on_delete=models.PROTECT, related_name="asiento_costo"
    )
    tipo = models.CharField("tipo", max_length=10, choices=TIPOS)
    orden = models.ForeignKey(
        OrdenTrabajo, on_delete=models.PROTECT, related_name="asientos"
    )
    registro = models.ForeignKey(
        RegistroCosto, on_delete=models.PROTECT, related_name="asientos"
    )
    clave_idempotencia = models.CharField(
        "clave de idempotencia", max_length=80, unique=True
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["registro", "tipo"], name="asiento_costo_unico_tipo"
            ),
        ]

    def __str__(self):
        return f"Asiento {self.transaccion_id} · {self.get_tipo_display()}"
