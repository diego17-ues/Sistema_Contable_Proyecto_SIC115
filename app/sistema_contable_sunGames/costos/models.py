"""Modelos del subsistema de costos: órdenes de trabajo y costeo real.

Este módulo NO escribe en las tablas del Libro Mayor. Los cargos se
registran aquí con su cuenta destino (serie 41 / intangible) y la
trazabilidad contable queda lista para una fase posterior.
"""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from catalogo.models import Cuenta
from libro_mayor.models import PeriodoContable

DINERO_MAX = 14
TASA_MAX = 12
HORAS_MAX = 10

CONCEPTOS_CUENTA = [
    ("mano_obra", "Mano de obra directa (4101)"),
    ("servicio_directo", "Servicios directos (4102)"),
    ("indirecto", "Costos indirectos (4103)"),
    ("intangible", "Intangible / videojuegos terminados"),
]

TIPOS_USO_EQUIPO = [
    ("EXCLUSIVO", "Uso exclusivo de un juego"),
    ("COMPARTIDO", "Uso compartido"),
    ("ADMINISTRACION", "Administración"),
    ("OCIOSO", "Ocioso"),
]


class Juego(models.Model):
    nombre = models.CharField("nombre", max_length=160, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class OrdenTrabajo(models.Model):
    """Una orden de trabajo por juego. Se cierra al lanzar el juego."""

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
    capitalizable_desde = models.DateField(
        "capitalizable desde", null=True, blank=True
    )
    fecha_cierre = models.DateField("fecha de cierre", null=True, blank=True)
    motivo_cierre = models.CharField("motivo de cierre", max_length=200, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="ordenes_creadas", null=True, blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"OT {self.pk} · {self.juego}"

    @property
    def abierta(self):
        return self.estado == self.ESTADO_ABIERTA

    @property
    def sin_fecha_capitalizacion(self):
        return self.capitalizable_desde is None


class Proceso(models.Model):
    """Proceso de desarrollo al que se imputan horas (programación, arte…)."""

    nombre = models.CharField("nombre", max_length=120, unique=True)
    descripcion = models.CharField("descripción", max_length=200, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class CostoProceso(models.Model):
    """Costo real del proceso en un período y sus horas base.

    tasa = costo / horas_base. ``tasa_presupuestada`` permite aplicar una
    tasa estimada en cortes provisionales.
    """

    proceso = models.ForeignKey(
        Proceso, on_delete=models.PROTECT, related_name="costos"
    )
    periodo = models.ForeignKey(
        PeriodoContable, on_delete=models.PROTECT, related_name="costos_proceso"
    )
    costo = models.DecimalField(
        "costo del proceso", max_digits=DINERO_MAX, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    horas_base = models.DecimalField(
        "horas base", max_digits=HORAS_MAX, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    tasa_presupuestada = models.DecimalField(
        "tasa presupuestada", max_digits=TASA_MAX, decimal_places=6,
        null=True, blank=True, validators=[MinValueValidator(0)],
    )

    class Meta:
        ordering = ["proceso__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["proceso", "periodo"], name="costo_proceso_unico"
            ),
        ]

    def __str__(self):
        return f"{self.proceso} · {self.periodo}"

    @property
    def tasa_real(self):
        if not self.horas_base:
            return None
        return self.costo / self.horas_base


class ParametroVigente(models.Model):
    """Parámetro con vigencia (horas semanales, tasa de cargas, etc.).

    ``verificado=False`` marca cifras pendientes de confirmación
    (tratamiento laboral/tributario: siempre VERIFICAR).
    """

    concepto = models.CharField("concepto", max_length=60)
    valor = models.DecimalField(
        "valor", max_digits=TASA_MAX, decimal_places=6,
        validators=[MinValueValidator(0)],
    )
    vigente_desde = models.DateField("vigente desde")
    vigente_hasta = models.DateField("vigente hasta", null=True, blank=True)
    verificado = models.BooleanField("verificado", default=False)
    descripcion = models.CharField("descripción", max_length=200, blank=True)

    class Meta:
        ordering = ["concepto", "-vigente_desde"]
        constraints = [
            models.UniqueConstraint(
                fields=["concepto", "vigente_desde"],
                name="parametro_concepto_vigencia",
            ),
        ]

    def __str__(self):
        return f"{self.concepto} = {self.valor}"


class SalarioReferencia(models.Model):
    """Salario bruto de referencia por rol, con vigencia."""

    rol = models.CharField("rol", max_length=60)
    salario_bruto = models.DecimalField(
        "salario bruto", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    vigente_desde = models.DateField("vigente desde")
    vigente_hasta = models.DateField("vigente hasta", null=True, blank=True)
    verificado = models.BooleanField("verificado", default=False)

    class Meta:
        ordering = ["rol", "-vigente_desde"]
        constraints = [
            models.UniqueConstraint(
                fields=["rol", "vigente_desde"], name="salario_rol_vigencia"
            ),
        ]

    def __str__(self):
        return f"{self.rol}: {self.salario_bruto}"


class MapeoCuenta(models.Model):
    """Concepto de costo → cuenta del catálogo real.

    Solo admite cuentas activas y de detalle (sin subcuentas), igual que
    el Libro Mayor. Si la cuenta no existe, el mapeo no se puede crear.
    """

    concepto = models.CharField(
        "concepto", max_length=30, choices=CONCEPTOS_CUENTA, unique=True
    )
    cuenta = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT, related_name="mapeos_costos"
    )

    class Meta:
        ordering = ["concepto"]

    def __str__(self):
        return f"{self.get_concepto_display()} → {self.cuenta.codigo}"


class RegistroHora(models.Model):
    """Horas pagadas registradas en una orden de trabajo."""

    orden = models.ForeignKey(
        OrdenTrabajo, on_delete=models.PROTECT, related_name="horas"
    )
    proceso = models.ForeignKey(
        Proceso, on_delete=models.PROTECT, null=True, blank=True,
        related_name="horas",
    )
    rol = models.CharField("rol", max_length=60)
    horas = models.DecimalField(
        "horas", max_digits=HORAS_MAX, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    fecha = models.DateField("fecha")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="horas_registradas", null=True, blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.rol} · {self.horas} h · OT {self.orden_id}"


class CargoOrden(models.Model):
    """Cargo de costo aplicado a una orden de trabajo.

    No escribe en el Libro Mayor: guarda la cuenta destino (snapshot del
    MapeoCuenta), la clave de idempotencia y la referencia futura al
    asiento contable.
    """

    ORIGEN_DIRECTO = "DIRECTO"
    ORIGEN_PROCESO = "PROCESO"
    ORIGEN_DEPRECIACION = "DEPRECIACION"
    ORIGEN_SERVICIO = "SERVICIO_ASIGNADO"
    ORIGEN_AJUSTE = "AJUSTE"
    ORIGENES = [
        (ORIGEN_DIRECTO, "Directo"),
        (ORIGEN_PROCESO, "Proceso"),
        (ORIGEN_DEPRECIACION, "Depreciación"),
        (ORIGEN_SERVICIO, "Servicio asignado"),
        (ORIGEN_AJUSTE, "Ajuste"),
    ]

    orden = models.ForeignKey(
        OrdenTrabajo, on_delete=models.PROTECT, related_name="cargos"
    )
    origen = models.CharField(
        "origen", max_length=20, choices=ORIGENES
    )
    concepto_cuenta = models.CharField(
        "concepto de cuenta", max_length=30, choices=CONCEPTOS_CUENTA,
        blank=True,
    )
    cuenta = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT, null=True, blank=True,
        related_name="cargos_orden",
        help_text="Cuenta destino snapshot (serie 41 o intangible).",
    )
    afecta_mayor = models.BooleanField("afecta al mayor", default=True)
    monto = models.DecimalField(
        "monto", max_digits=DINERO_MAX, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    fecha = models.DateField("fecha")
    descripcion = models.CharField("descripción", max_length=200)
    proceso = models.ForeignKey(
        Proceso, on_delete=models.PROTECT, null=True, blank=True,
        related_name="cargos",
    )
    equipo = models.ForeignKey(
        "Equipo", on_delete=models.PROTECT, null=True, blank=True,
        related_name="cargos",
    )
    fondo = models.ForeignKey(
        "FondoCompartido", on_delete=models.PROTECT, null=True, blank=True,
        related_name="cargos",
    )
    registro_hora = models.ForeignKey(
        RegistroHora, on_delete=models.PROTECT, null=True, blank=True,
        related_name="cargos",
    )
    clave_idempotencia = models.CharField(
        "clave de idempotencia", max_length=80, unique=True,
        null=True, blank=True,
    )
    referencia_asiento = models.CharField(
        "referencia al asiento", max_length=80, blank=True,
        help_text="Se llena cuando exista el mecanismo de asientos.",
    )
    corte = models.ForeignKey(
        "CorteCostos", on_delete=models.PROTECT, null=True, blank=True,
        related_name="cargos",
        help_text="Corte provisional vigente que traslada el saldo.",
    )
    traslado_intangible = models.DateField(
        "trasladado a intangible", null=True, blank=True,
        help_text="Fecha del traslado definitivo (cierre/corte final).",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="cargos_registrados", null=True, blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.get_origen_display()} ${self.monto} · OT {self.orden_id}"


class FondoCompartido(models.Model):
    """Fondo de servicios de terceros a repartir entre órdenes.

    Se distribuye una sola vez, por horas de desarrollo, con ajuste de
    centavos en la última orden. Los cargos generados tienen
    ``afecta_mayor=False`` (gasto del período, no pasa por la serie 41).
    """

    ESTADO_PENDIENTE = "PENDIENTE"
    ESTADO_DISTRIBUIDO = "DISTRIBUIDO"
    ESTADOS = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_DISTRIBUIDO, "Distribuido"),
    ]

    nombre = models.CharField("nombre", max_length=120)
    monto = models.DecimalField(
        "monto", max_digits=DINERO_MAX, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    fecha = models.DateField("fecha")
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    estado = models.CharField(
        "estado", max_length=12, choices=ESTADOS, default=ESTADO_PENDIENTE
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="fondos_creados", null=True, blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.nombre} · ${self.monto}"


class Equipo(models.Model):
    """Activo de equipo para costeo (depreciación línea recta)."""

    nombre = models.CharField("nombre", max_length=120)
    costo = models.DecimalField(
        "costo", max_digits=DINERO_MAX, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    valor_residual = models.DecimalField(
        "valor residual", max_digits=DINERO_MAX, decimal_places=2,
        default=0, validators=[MinValueValidator(0)],
    )
    vida_util_meses = models.PositiveIntegerField(
        "vida útil (meses)", validators=[MinValueValidator(1)]
    )
    tipo_uso = models.CharField(
        "tipo de uso", max_length=15, choices=TIPOS_USO_EQUIPO,
        default="COMPARTIDO",
    )
    orden = models.ForeignKey(
        OrdenTrabajo, on_delete=models.PROTECT, null=True, blank=True,
        related_name="equipos",
        help_text="Obligatorio cuando el uso es exclusivo.",
    )
    horas_mes = models.DecimalField(
        "horas máquina por mes", max_digits=HORAS_MAX, decimal_places=2,
        default=0, validators=[MinValueValidator(0)],
        help_text="Capacidad mensual; base de la tasa por hora máquina.",
    )
    fecha_adquisicion = models.DateField("fecha de adquisición")
    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def cuota_mensual(self):
        """Depreciación línea recta: (costo - residual) / vida útil."""
        base = self.costo - self.valor_residual
        if base <= 0 or not self.vida_util_meses:
            return None
        return base / self.vida_util_meses


class UsoEquipo(models.Model):
    """Horas máquina de un equipo en una orden durante un período."""

    equipo = models.ForeignKey(
        Equipo, on_delete=models.PROTECT, related_name="usos"
    )
    orden = models.ForeignKey(
        OrdenTrabajo, on_delete=models.PROTECT, related_name="usos_equipo"
    )
    fecha = models.DateField("fecha")
    horas = models.DecimalField(
        "horas máquina", max_digits=HORAS_MAX, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.equipo} · {self.horas} h · OT {self.orden_id}"


class CorteCostos(models.Model):
    """Corte de costos del período (provisional reversible o definitivo).

    Traslada los saldos capitalizables de la serie 41 al intangible sin
    tocar el Libro Mayor. El provisional se revierte; el definitivo no.
    """

    TIPO_PROVISIONAL = "PROVISIONAL"
    TIPO_DEFINITIVO = "DEFINITIVO"
    TIPOS = [
        (TIPO_PROVISIONAL, "Provisional (reversible)"),
        (TIPO_DEFINITIVO, "Definitivo"),
    ]

    ESTADO_VIGENTE = "VIGENTE"
    ESTADO_REVERTIDO = "REVERTIDO"
    ESTADOS = [
        (ESTADO_VIGENTE, "Vigente"),
        (ESTADO_REVERTIDO, "Revertido"),
    ]

    periodo = models.ForeignKey(
        PeriodoContable, on_delete=models.PROTECT, related_name="cortes_costos"
    )
    tipo = models.CharField("tipo", max_length=12, choices=TIPOS)
    fecha = models.DateField("fecha de corte")
    estado = models.CharField(
        "estado", max_length=10, choices=ESTADOS, default=ESTADO_VIGENTE
    )
    motivo = models.CharField("motivo", max_length=200)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="cortes_costos", null=True, blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"Corte {self.get_tipo_display()} · {self.periodo}"


class CorteDetalle(models.Model):
    """Línea del corte: saldo por orden y cuenta de la serie 41."""

    corte = models.ForeignKey(
        CorteCostos, on_delete=models.CASCADE, related_name="detalles"
    )
    orden = models.ForeignKey(
        OrdenTrabajo, on_delete=models.PROTECT, related_name="detalles_corte"
    )
    cuenta = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT, related_name="detalles_corte"
    )
    monto = models.DecimalField(
        "monto", max_digits=DINERO_MAX, decimal_places=2
    )

    class Meta:
        ordering = ["orden_id", "cuenta_id"]

    def __str__(self):
        return f"OT {self.orden_id} · {self.cuenta.codigo} · ${self.monto}"
