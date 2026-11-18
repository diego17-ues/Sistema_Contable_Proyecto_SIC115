"""Acceso a datos del subsistema de costos (ORM encapsulado)."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum

from catalogo.models import Cuenta
from libro_mayor.models import EstadoPeriodo, PeriodoContable

from .models import (
    CargoOrden,
    CostoProceso,
    CorteCostos,
    CorteDetalle,
    Equipo,
    FondoCompartido,
    Juego,
    MapeoCuenta,
    OrdenTrabajo,
    ParametroVigente,
    Proceso,
    RegistroHora,
    SalarioReferencia,
    UsoEquipo,
)


class CostosRepository:
    # ---- Juegos y órdenes ----
    def juegos(self):
        return Juego.objects.all()

    def obtener_juego(self, juego_id):
        return Juego.objects.get(pk=juego_id)

    def juego_por_nombre(self, nombre):
        return Juego.objects.filter(nombre__iexact=nombre.strip()).first()

    def crear_juego(self, *, nombre):
        return Juego.objects.create(nombre=nombre.strip())

    def ordenes(self, *, estado=None, juego_id=None):
        qs = OrdenTrabajo.objects.select_related("juego").order_by("-id")
        if estado:
            qs = qs.filter(estado=estado)
        if juego_id:
            qs = qs.filter(juego_id=juego_id)
        return qs

    def obtener_orden(self, orden_id):
        return OrdenTrabajo.objects.select_related("juego").get(pk=orden_id)

    def orden_por_juego(self, juego):
        return OrdenTrabajo.objects.filter(juego=juego).first()

    def crear_orden(self, *, juego, capitalizable_desde, usuario):
        return OrdenTrabajo.objects.create(
            juego=juego, capitalizable_desde=capitalizable_desde,
            creado_por=usuario,
        )

    def guardar_orden(self, orden):
        orden.save()
        return orden

    # ---- Procesos y costos de proceso ----
    def procesos(self):
        return Proceso.objects.all()

    def crear_proceso(self, *, nombre, descripcion=""):
        return Proceso.objects.create(nombre=nombre.strip(), descripcion=descripcion)

    def costos_proceso(self, periodo):
        return CostoProceso.objects.filter(periodo=periodo).select_related(
            "proceso"
        )

    def crear_costo_proceso(self, *, proceso, periodo, costo, horas_base,
                            tasa_presupuestada=None):
        return CostoProceso.objects.create(
            proceso=proceso, periodo=periodo, costo=costo,
            horas_base=horas_base, tasa_presupuestada=tasa_presupuestada,
        )

    # ---- Parámetros, salarios y mapeos ----
    def parametros(self):
        return ParametroVigente.objects.all()

    def crear_parametro(self, **datos):
        return ParametroVigente.objects.create(**datos)

    def parametro_vigente(self, concepto, fecha):
        return ParametroVigente.objects.filter(
            concepto=concepto, vigente_desde__lte=fecha,
        ).filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha)
        ).order_by("-vigente_desde").first()

    def salarios(self):
        return SalarioReferencia.objects.all()

    def crear_salario(self, **datos):
        return SalarioReferencia.objects.create(**datos)

    def salario_vigente(self, rol, fecha):
        return SalarioReferencia.objects.filter(
            rol=rol, vigente_desde__lte=fecha,
        ).filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha)
        ).order_by("-vigente_desde").first()

    def mapeos(self):
        return MapeoCuenta.objects.select_related("cuenta__rubro").all()

    def crear_mapeo(self, *, concepto, cuenta):
        return MapeoCuenta.objects.create(concepto=concepto, cuenta=cuenta)

    def mapeo(self, concepto):
        return MapeoCuenta.objects.filter(concepto=concepto).first()

    def cuenta(self, codigo):
        try:
            return Cuenta.objects.get(codigo=codigo)
        except Cuenta.DoesNotExist:
            return None

    def cuentas_posteables(self):
        """Cuentas activas del catálogo real (todas son de detalle:
        el código siempre tiene 4 dígitos, sin subcuentas)."""
        return Cuenta.objects.filter(activa=True).order_by("codigo")

    # ---- Horas ----
    def crear_hora(self, **datos):
        return RegistroHora.objects.create(**datos)

    def horas_de_orden(self, orden):
        return RegistroHora.objects.filter(orden=orden)

    def horas_por_orden(self, *, proceso=None, periodo=None, hasta=None):
        qs = RegistroHora.objects.filter(orden__estado=OrdenTrabajo.ESTADO_ABIERTA)
        if proceso is not None:
            qs = qs.filter(proceso=proceso)
        if periodo is not None:
            qs = qs.filter(fecha__gte=periodo.fecha_inicio,
                           fecha__lte=periodo.fecha_fin)
        if hasta is not None:
            qs = qs.filter(fecha__lte=hasta)
        return qs.values("orden_id").annotate(total=Sum("horas"))

    def horas_en_periodo(self, proceso, periodo):
        return RegistroHora.objects.filter(
            proceso=proceso, orden__estado=OrdenTrabajo.ESTADO_ABIERTA,
            fecha__gte=periodo.fecha_inicio,
            fecha__lte=periodo.fecha_fin,
        ).values("orden_id").annotate(total=Sum("horas"))

    # ---- Cargos ----
    def crear_cargo(self, **datos):
        return CargoOrden.objects.create(**datos)

    def cargos_de_orden(self, orden):
        return CargoOrden.objects.filter(orden=orden).select_related(
            "cuenta", "proceso", "equipo", "fondo", "corte"
        )

    def cargo_por_clave(self, clave):
        return CargoOrden.objects.filter(clave_idempotencia=clave).first()

    def monto_proceso_aplicado(self, costo, periodo):
        """Total ya aplicado de un CostoProceso en un período (incluye
        corridas anteriores: la clave de idempotencia lo garantiza)."""
        return CargoOrden.objects.filter(
            origen=CargoOrden.ORIGEN_PROCESO,
            clave_idempotencia__startswith=(
                f"proc-{costo.pk}-{periodo.pk}-"
            ),
        ).aggregate(total=Sum("monto"))["total"] or Decimal("0")

    def cargos_corte_vigente(self, orden):
        return CargoOrden.objects.filter(
            orden=orden, corte__estado=CorteCostos.ESTADO_VIGENTE,
            corte__tipo=CorteCostos.TIPO_PROVISIONAL,
            traslado_intangible__isnull=True,
        )

    def cargos_capitalizables(self, orden):
        """Cargos que afectan el mayor y no fueron trasladados."""
        qs = CargoOrden.objects.filter(
            orden=orden, afecta_mayor=True, cuenta__isnull=False,
            traslado_intangible__isnull=True,
        )
        if orden.capitalizable_desde:
            qs = qs.filter(fecha__gte=orden.capitalizable_desde)
        else:
            qs = qs.none()
        return qs

    def cargos_capitalizables_sin_traslado(self, orden):
        """Cargos capitalizables de la orden aún en la serie 41 (incluye
        los marcados por un corte provisional vigente)."""
        qs = CargoOrden.objects.filter(
            orden=orden, afecta_mayor=True, cuenta__isnull=False,
            traslado_intangible__isnull=True,
        )
        if orden.capitalizable_desde:
            qs = qs.filter(fecha__gte=orden.capitalizable_desde)
        else:
            qs = qs.none()
        return qs.select_related("corte")

    def cargos_para_corte(self, fecha):
        """Cargos capitalizables candidatos a un corte: afectan el mayor,
        tienen cuenta, no están trasladados ni ya en un corte."""
        return CargoOrden.objects.filter(
            afecta_mayor=True, cuenta__isnull=False,
            traslado_intangible__isnull=True, corte__isnull=True,
            fecha__lte=fecha,
        ).select_related("orden", "cuenta")

    def guardar_cargo(self, cargo):
        cargo.save()
        return cargo

    def cargos_del_periodo(self, periodo):
        return CargoOrden.objects.filter(
            fecha__gte=periodo.fecha_inicio, fecha__lte=periodo.fecha_fin
        ).select_related("orden__juego", "cuenta")

    # ---- Fondos ----
    def fondos(self):
        return FondoCompartido.objects.all()

    def obtener_fondo(self, fondo_id):
        return FondoCompartido.objects.get(pk=fondo_id)

    def crear_fondo(self, **datos):
        return FondoCompartido.objects.create(**datos)

    def guardar_fondo(self, fondo):
        fondo.save()
        return fondo

    # ---- Equipos y usos ----
    def equipos(self):
        return Equipo.objects.select_related("orden__juego").all()

    def obtener_equipo(self, equipo_id):
        return Equipo.objects.get(pk=equipo_id)

    def crear_equipo(self, **datos):
        return Equipo.objects.create(**datos)

    def guardar_equipo(self, equipo):
        equipo.save()
        return equipo

    def crear_uso_equipo(self, **datos):
        return UsoEquipo.objects.create(**datos)

    def usos_en_mes(self, equipo, anio, mes):
        return UsoEquipo.objects.filter(
            equipo=equipo, fecha__year=anio, fecha__month=mes,
            orden__estado=OrdenTrabajo.ESTADO_ABIERTA,
        ).values("orden_id").annotate(total=Sum("horas"))

    def horas_orden_en_mes(self, orden, anio, mes):
        return RegistroHora.objects.filter(
            orden=orden, fecha__year=anio, fecha__month=mes,
        ).aggregate(total=Sum("horas"))["total"] or Decimal("0")

    # ---- Cortes ----
    def cortes(self):
        return CorteCostos.objects.select_related("periodo", "usuario")

    def obtener_corte(self, corte_id):
        return CorteCostos.objects.get(pk=corte_id)

    def crear_corte(self, **datos):
        return CorteCostos.objects.create(**datos)

    def crear_detalle_corte(self, **datos):
        return CorteDetalle.objects.create(**datos)

    def guardar_corte(self, corte):
        corte.save()
        return corte

    # ---- Períodos y transacciones ----
    def periodos(self):
        return PeriodoContable.objects.all()

    def obtener_periodo(self, periodo_id):
        return PeriodoContable.objects.get(pk=periodo_id)

    def periodo_abierto(self):
        return PeriodoContable.objects.filter(
            estado=EstadoPeriodo.ABIERTO
        ).order_by("-fecha_inicio").first()

    def periodos_de_fecha(self, fecha):
        return PeriodoContable.objects.que_contienen(fecha)

    def periodo_con_rango(self, inicio, fin):
        return PeriodoContable.objects.filter(
            fecha_inicio=inicio, fecha_fin=fin
        ).first()

    @staticmethod
    @transaction.atomic
    def en_transaccion():
        return transaction.atomic()
