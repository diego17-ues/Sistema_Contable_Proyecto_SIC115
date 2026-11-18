from django.conf import settings
from django.db import models

from .exceptions import VersionInmutableError

HORAS_DECIMALES = 4
TARIFA_DECIMALES = 4
MONTO_MAX_DIGITS = 14
MONTO_DECIMALES = 2


class Rol(models.Model):
    """Puesto de desarrollo con su nivel; no es un rol de usuario."""

    nombre = models.CharField("nombre", max_length=80, unique=True)
    nivel = models.PositiveIntegerField("nivel")

    class Meta:
        ordering = ["nivel", "nombre"]
        verbose_name = "rol de estimación"
        verbose_name_plural = "roles de estimación"

    def __str__(self):
        return f"{self.nombre} (nivel {self.nivel})"


class SalarioReferencia(models.Model):
    """Salario bruto mensual por rol y nivel, con vigencia."""

    rol = models.ForeignKey(
        Rol, on_delete=models.PROTECT, related_name="salarios"
    )
    salario_bruto = models.DecimalField(
        "salario bruto", max_digits=MONTO_MAX_DIGITS,
        decimal_places=MONTO_DECIMALES,
    )
    vigente_desde = models.DateField("vigente desde")
    vigente_hasta = models.DateField(
        "vigente hasta", null=True, blank=True
    )

    class Meta:
        ordering = ["rol__nivel", "rol__nombre", "vigente_desde"]
        verbose_name = "salario de referencia"
        verbose_name_plural = "salarios de referencia"
        constraints = [
            models.CheckConstraint(
                check=models.Q(salario_bruto__gte=0),
                name="salario_bruto_no_negativo",
            ),
            models.CheckConstraint(
                check=models.Q(vigente_hasta__isnull=True)
                | models.Q(vigente_hasta__gte=models.F("vigente_desde")),
                name="salario_vigencia_valida",
            ),
        ]

    def __str__(self):
        return f"{self.rol} {self.salario_bruto}"


class ParametroVigente(models.Model):
    """Parámetro con fecha de vigencia; nunca se fija en el código."""

    clave = models.CharField("clave", max_length=60)
    valor = models.DecimalField(
        "valor", max_digits=14, decimal_places=6
    )
    vigente_desde = models.DateField("vigente desde")
    vigente_hasta = models.DateField(
        "vigente hasta", null=True, blank=True
    )
    verificado = models.BooleanField("verificado", default=False)

    class Meta:
        ordering = ["clave", "vigente_desde"]
        verbose_name = "parámetro vigente"
        verbose_name_plural = "parámetros vigentes"
        constraints = [
            models.CheckConstraint(
                check=models.Q(vigente_hasta__isnull=True)
                | models.Q(vigente_hasta__gte=models.F("vigente_desde")),
                name="parametro_vigencia_valida",
            ),
        ]

    def __str__(self):
        return f"{self.clave}={self.valor}"


class Juego(models.Model):
    nombre = models.CharField("nombre", max_length=150, unique=True)
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "juego"
        verbose_name_plural = "juegos"

    def __str__(self):
        return self.nombre


class ClasificacionContable(models.TextChoices):
    CAPEX = "CAPEX", "Capitalizable (CAPEX)"
    OPEX = "OPEX", "Gasto del período (OPEX)"
    MIXTO = "MIXTO", "Mixto (OPEX/CAPEX)"


class FaseEstimacion(models.Model):
    juego = models.ForeignKey(
        Juego, on_delete=models.PROTECT, related_name="fases"
    )
    nombre = models.CharField("nombre", max_length=120)
    orden = models.PositiveIntegerField("orden")
    clasificacion = models.CharField(
        "clasificación contable", max_length=10,
        choices=ClasificacionContable.choices,
        default=ClasificacionContable.OPEX,
    )

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "fase de estimación"
        verbose_name_plural = "fases de estimación"
        constraints = [
            models.UniqueConstraint(
                fields=["juego", "orden"], name="fase_orden_unico_por_juego"
            ),
            models.UniqueConstraint(
                fields=["juego", "nombre"], name="fase_nombre_unico_por_juego"
            ),
        ]

    def __str__(self):
        return f"{self.juego}: {self.nombre}"


class Experto(models.Model):
    nombre = models.CharField("nombre", max_length=150, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "experto"
        verbose_name_plural = "expertos"

    def __str__(self):
        return self.nombre


class EstimacionExperto(models.Model):
    """Estimación PERT de un experto para una fase, rol y ronda."""

    juego = models.ForeignKey(
        Juego, on_delete=models.PROTECT, related_name="estimaciones"
    )
    fase = models.ForeignKey(
        FaseEstimacion, on_delete=models.PROTECT,
        related_name="estimaciones",
    )
    rol = models.ForeignKey(
        Rol, on_delete=models.PROTECT, related_name="estimaciones"
    )
    experto = models.ForeignKey(
        Experto, on_delete=models.PROTECT, related_name="estimaciones"
    )
    ronda = models.PositiveIntegerField("ronda")
    optimista = models.DecimalField(
        "optimista (O)", max_digits=10,
        decimal_places=HORAS_DECIMALES,
    )
    moda = models.DecimalField(
        "más probable (M)", max_digits=10,
        decimal_places=HORAS_DECIMALES,
    )
    pesimista = models.DecimalField(
        "pesimista (P)", max_digits=10,
        decimal_places=HORAS_DECIMALES,
    )
    justificacion = models.TextField("justificación", blank=True)

    class Meta:
        ordering = ["fase__orden", "rol__nivel", "rol__nombre", "ronda"]
        verbose_name = "estimación de experto"
        verbose_name_plural = "estimaciones de expertos"
        constraints = [
            models.CheckConstraint(
                check=models.Q(optimista__gte=0)
                & models.Q(moda__gte=0)
                & models.Q(pesimista__gte=0),
                name="estimacion_horas_no_negativas",
            ),
            models.CheckConstraint(
                check=models.Q(optimista__lte=models.F("moda"))
                & models.Q(moda__lte=models.F("pesimista")),
                name="estimacion_omp_ordenado",
            ),
            models.UniqueConstraint(
                fields=["juego", "fase", "rol", "experto", "ronda"],
                name="estimacion_unica_por_ronda",
            ),
        ]

    def __str__(self):
        return f"{self.fase} / {self.rol} ronda {self.ronda}"


class RondaDelphi(models.Model):
    juego = models.ForeignKey(
        Juego, on_delete=models.PROTECT, related_name="rondas"
    )
    numero = models.PositiveIntegerField("número")
    cerrada = models.BooleanField("cerrada", default=False)
    aprobada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="aprobada por",
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="rondas_delphi_aprobadas",
    )
    # Resultado de la consolidación por fase/rol al cerrar la ronda.
    resultado = models.JSONField("resultado", null=True, blank=True)

    class Meta:
        ordering = ["juego", "numero"]
        verbose_name = "ronda Delphi"
        verbose_name_plural = "rondas Delphi"
        constraints = [
            models.UniqueConstraint(
                fields=["juego", "numero"], name="ronda_unica_por_juego"
            ),
        ]

    def __str__(self):
        return f"{self.juego} ronda {self.numero}"


class EstadoVersion(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    APROBADO = "APROBADO", "Aprobado"
    VIGENTE = "VIGENTE", "Vigente"


class VersionPresupuesto(models.Model):
    """Versión del presupuesto estimado de un juego.

    Una versión aprobada o vigente es inmutable: cualquier corrección crea
    una versión nueva con el siguiente número.
    """

    Estado = EstadoVersion

    juego = models.ForeignKey(
        Juego, on_delete=models.PROTECT, related_name="versiones"
    )
    numero = models.PositiveIntegerField("número")
    estado = models.CharField(
        "estado", max_length=20, choices=EstadoVersion.choices,
        default=Estado.BORRADOR,
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="autor",
        on_delete=models.PROTECT, related_name="versiones_presupuesto",
    )
    fecha = models.DateTimeField("fecha", auto_now_add=True)
    snapshot_parametros = models.JSONField(
        "parámetros usados", default=dict
    )

    class Meta:
        ordering = ["juego", "-numero"]
        verbose_name = "versión de presupuesto"
        verbose_name_plural = "versiones de presupuesto"
        constraints = [
            models.UniqueConstraint(
                fields=["juego", "numero"], name="version_unica_por_juego"
            ),
            models.CheckConstraint(
                check=models.Q(estado__in=EstadoVersion.values),
                name="version_estado_valido",
            ),
        ]

    def __str__(self):
        return f"{self.juego} v{self.numero} ({self.get_estado_display()})"

    @property
    def inmutable(self):
        return self.estado != self.Estado.BORRADOR

    def save(self, *args, **kwargs):
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).values_list(
                "estado", flat=True
            ).first()
            if anterior in (
                self.Estado.APROBADO, self.Estado.VIGENTE
            ):
                self._verificar_cambio_permitido(anterior)
        super().save(*args, **kwargs)

    def _verificar_cambio_permitido(self, anterior):
        permitidas = {
            (self.Estado.APROBADO, self.Estado.VIGENTE),
            (self.Estado.VIGENTE, self.Estado.APROBADO),
        }
        if (anterior, self.estado) not in permitidas:
            raise VersionInmutableError()

    def delete(self, *args, **kwargs):
        raise VersionInmutableError(
            "Las versiones de presupuesto no se eliminan."
        )


class LineaPresupuesto(models.Model):
    version = models.ForeignKey(
        VersionPresupuesto, on_delete=models.PROTECT,
        related_name="lineas",
    )
    fase = models.ForeignKey(
        FaseEstimacion, on_delete=models.PROTECT, related_name="lineas"
    )
    rol = models.ForeignKey(
        Rol, on_delete=models.PROTECT, related_name="lineas"
    )
    horas_E = models.DecimalField(
        "horas E", max_digits=12,
        decimal_places=HORAS_DECIMALES,
    )
    sigma = models.DecimalField(
        "σ", max_digits=12, decimal_places=HORAS_DECIMALES
    )
    tarifa = models.DecimalField(
        "tarifa efectiva", max_digits=14,
        decimal_places=TARIFA_DECIMALES,
    )
    costo_mano_obra = models.DecimalField(
        "costo de mano de obra", max_digits=MONTO_MAX_DIGITS,
        decimal_places=MONTO_DECIMALES,
    )

    class Meta:
        ordering = ["fase__orden", "rol__nivel", "rol__nombre"]
        verbose_name = "línea de presupuesto"
        verbose_name_plural = "líneas de presupuesto"
        constraints = [
            models.UniqueConstraint(
                fields=["version", "fase", "rol"],
                name="linea_unica_por_version",
            ),
        ]

    def __str__(self):
        return f"{self.fase} / {self.rol}"


class CostoDirectoEstimado(models.Model):
    version = models.ForeignKey(
        VersionPresupuesto, on_delete=models.PROTECT,
        related_name="costos_directos",
    )
    concepto = models.CharField("concepto", max_length=150)
    monto = models.DecimalField(
        "monto", max_digits=MONTO_MAX_DIGITS,
        decimal_places=MONTO_DECIMALES,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "costo directo estimado"
        verbose_name_plural = "costos directos estimados"

    def __str__(self):
        return f"{self.concepto} {self.monto}"


class CostoIndirectoEstimado(models.Model):
    version = models.ForeignKey(
        VersionPresupuesto, on_delete=models.PROTECT,
        related_name="costos_indirectos",
    )
    departamento = models.CharField("departamento", max_length=80)
    monto = models.DecimalField(
        "monto", max_digits=MONTO_MAX_DIGITS,
        decimal_places=MONTO_DECIMALES,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "costo indirecto estimado"
        verbose_name_plural = "costos indirectos estimados"

    def __str__(self):
        return f"{self.departamento} {self.monto}"
