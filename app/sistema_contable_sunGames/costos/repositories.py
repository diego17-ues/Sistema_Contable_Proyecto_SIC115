"""Repositorio del subsistema de costos: encapsula el acceso al ORM."""

from django.db.models import Exists, Min, OuterRef, Q, Sum

from catalogo.models import Cuenta
from estimacion.models import EstadoVersion, VersionPresupuesto
from libro_mayor.models import (
    EstadoPeriodo,
    Movimiento,
    PeriodoContable,
)

from .models import (
    AsientoCosto,
    ConfiguracionCuentaCosto,
    CuentaIndirectaExcluida,
    FuenteIndirecta,
    Juego,
    OrdenTrabajo,
    Proceso,
    RegistroCosto,
)


class CostosRepository:
    # ---- Juegos y órdenes ----
    def juego_por_nombre(self, nombre):
        return Juego.objects.filter(nombre__iexact=nombre).first()

    def crear_juego(self, *, nombre):
        return Juego.objects.create(nombre=nombre)

    def ordenes(self, *, estado=None, incluir_eliminadas=False):
        qs = OrdenTrabajo.objects.select_related("juego").annotate(
            total_vigente=Sum(
                "registros__importe",
                filter=Q(registros__estado=RegistroCosto.ESTADO_VIGENTE),
            )
        )
        if incluir_eliminadas:
            qs = qs.filter(eliminado_en__isnull=False)
        else:
            qs = qs.filter(eliminado_en__isnull=True)
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def ordenes_rendimiento(self):
        """Órdenes con totales reales y estimaciones precargadas."""
        return (self.ordenes()
                .select_related("estimacion_ref", "estimacion_ref__juego")
                .prefetch_related(
                    "estimacion_ref__lineas",
                    "estimacion_ref__costos_directos",
                    "estimacion_ref__costos_indirectos",
                ))

    def obtener_orden(self, orden_id, *, incluir_eliminada=False):
        qs = (OrdenTrabajo.objects
                .select_related("juego", "estimacion_ref",
                                "estimacion_ref__juego"))
        if not incluir_eliminada:
            qs = qs.filter(eliminado_en__isnull=True)
        return qs.filter(pk=orden_id).first()

    def orden_por_juego(self, juego):
        return OrdenTrabajo.objects.filter(
            juego=juego, eliminado_en__isnull=True
        ).first()

    def hay_otra_orden_activa(self, orden):
        return OrdenTrabajo.objects.filter(
            juego=orden.juego, eliminado_en__isnull=True
        ).exclude(pk=orden.pk).exists()

    def estimacion_en_otra_orden_activa(self, orden):
        if orden.estimacion_ref_id is None:
            return False
        return OrdenTrabajo.objects.filter(
            estimacion_ref_id=orden.estimacion_ref_id,
            eliminado_en__isnull=True,
        ).exclude(pk=orden.pk).exists()

    def crear_orden(self, *, juego, fecha_inicio, usuario,
                    estimacion_ref=None):
        return OrdenTrabajo.objects.create(
            juego=juego, fecha_inicio=fecha_inicio, creado_por=usuario,
            estimacion_ref=estimacion_ref,
        )

    def guardar_orden(self, orden):
        orden.save()
        return orden

    def guardar_juego(self, juego):
        juego.save()
        return juego

    def primera_fecha_registro_orden(self, orden):
        return RegistroCosto.objects.filter(orden=orden).aggregate(
            fecha=Min("fecha")
        )["fecha"]

    # ---- Estimación (solo lectura) ----
    def versiones_vinculables(self):
        return (VersionPresupuesto.objects.select_related("juego")
                .filter(estado__in=[
                    EstadoVersion.BORRADOR,
                    EstadoVersion.APROBADO,
                    EstadoVersion.VIGENTE,
                ], eliminado_en__isnull=True)
                .order_by("juego__nombre", "-numero"))

    def versiones_disponibles(self, *, orden_id=None):
        vinculaciones = OrdenTrabajo.objects.filter(
            estimacion_ref_id=OuterRef("pk"),
            eliminado_en__isnull=True,
        )
        if orden_id is not None:
            vinculaciones = vinculaciones.exclude(pk=orden_id)
        return (self.versiones_vinculables().annotate(
            vinculada_a_otra_orden=Exists(vinculaciones)
        ).filter(vinculada_a_otra_orden=False))

    def obtener_version_disponible(self, version_id, *, orden_id=None):
        return (self.versiones_disponibles(orden_id=orden_id)
                .filter(pk=version_id).first())

    # ---- Procesos ----
    def procesos(self, *, solo_activos=False):
        qs = Proceso.objects.all()
        return qs.filter(activo=True) if solo_activos else qs

    def obtener_proceso(self, proceso_id):
        return Proceso.objects.filter(pk=proceso_id).first()

    def crear_proceso(self, **datos):
        return Proceso.objects.create(**datos)

    def guardar_proceso(self, proceso):
        proceso.save()
        return proceso

    # ---- Configuración de cuentas ----
    def configuraciones(self):
        return ConfiguracionCuentaCosto.objects.select_related(
            "cuenta_costo", "contrapartida_defecto"
        ).prefetch_related("contrapartidas")

    def configuracion(self, elemento):
        return self.configuraciones().filter(elemento=elemento).first()

    def guardar_configuracion(self, *, elemento, cuenta_costo, contrapartidas,
                              contrapartida_defecto):
        config, _ = ConfiguracionCuentaCosto.objects.update_or_create(
            elemento=elemento,
            defaults={"cuenta_costo": cuenta_costo,
                      "contrapartida_defecto": contrapartida_defecto},
        )
        config.contrapartidas.set(contrapartidas)
        return config

    def cuentas_posteables(self):
        return (Cuenta.objects.filter(activa=True)
                .select_related("rubro").order_by("codigo"))

    def obtener_cuenta(self, cuenta_id):
        return Cuenta.objects.filter(pk=cuenta_id).first()

    # ---- Fuentes de costos indirectos ----
    def fuentes_indirectas(self, *, solo_activas=False):
        qs = FuenteIndirecta.objects.select_related(
            "cuenta_origen", "proceso"
        )
        if solo_activas:
            qs = qs.filter(activa=True, exclusiva_desarrollo=True)
        return qs

    def fuente_indirecta(self, fuente_id):
        return self.fuentes_indirectas().filter(pk=fuente_id).first()

    def crear_fuente_indirecta(self, **datos):
        return FuenteIndirecta.objects.create(**datos)

    def guardar_fuente_indirecta(self, fuente):
        fuente.save()
        return fuente

    def cuentas_indirectas_excluidas(self):
        return CuentaIndirectaExcluida.objects.select_related(
            "cuenta", "creada_por"
        ).all()

    def cuenta_indirecta_excluida(self, cuenta):
        return CuentaIndirectaExcluida.objects.filter(cuenta=cuenta).first()

    def excluir_cuenta_indirecta(self, *, cuenta, motivo, actor):
        return CuentaIndirectaExcluida.objects.create(
            cuenta=cuenta, motivo=motivo, creada_por=actor
        )

    def eliminar_exclusion_indirecta(self, exclusion):
        exclusion.delete()

    def cuentas_fuentes_disponibles(self):
        ocupadas = FuenteIndirecta.objects.values("cuenta_origen_id")
        excluidas = CuentaIndirectaExcluida.objects.values("cuenta_id")
        return (Cuenta.objects.filter(activa=True)
                .filter(rubro__codigo="4")
                .exclude(pk__in=ocupadas)
                .exclude(pk__in=excluidas)
                .order_by("codigo"))

    def periodos_contables(self, *, solo_abiertos=False):
        qs = PeriodoContable.objects.all().order_by(
            "-fecha_inicio", "-pk"
        )
        if solo_abiertos:
            qs = qs.filter(estado=EstadoPeriodo.ABIERTO)
        return qs

    def obtener_periodo_contable(self, periodo_id):
        try:
            return PeriodoContable.objects.filter(pk=periodo_id).first()
        except (TypeError, ValueError):
            return None

    def saldo_cuenta_periodo(self, cuenta, periodo):
        total = Movimiento.objects.filter(
            cuenta=cuenta,
            fecha__gte=periodo.fecha_inicio,
            fecha__lte=periodo.fecha_fin,
        ).aggregate(total=Sum("importe"))["total"]
        return total or 0

    def horas_por_orden_periodo(self, periodo, *, proceso=None):
        filtro = Q(
            registros__elemento="MANO_OBRA",
            registros__estado=RegistroCosto.ESTADO_VIGENTE,
            registros__fecha__gte=periodo.fecha_inicio,
            registros__fecha__lte=periodo.fecha_fin,
        )
        if proceso is not None:
            filtro &= Q(registros__proceso=proceso)
        return list(
            OrdenTrabajo.objects.filter(
                estado=OrdenTrabajo.ESTADO_ABIERTA,
                eliminado_en__isnull=True,
            ).select_related("juego").annotate(
                horas=Sum("registros__horas", filter=filtro)
            ).filter(horas__gt=0).order_by("pk")
        )

    def registros_fuente_periodo(self, fuente, periodo):
        return (RegistroCosto.objects.filter(
            fuente_indirecta=fuente, periodo_indirecto=periodo,
        ).select_related("orden", "proceso")
                .prefetch_related("asientos").order_by("orden_id", "pk"))

    def registros_indirectos_periodo(self, periodo):
        return (RegistroCosto.objects.filter(
            fuente_indirecta__isnull=False,
            periodo_indirecto=periodo,
        ).select_related(
            "orden", "orden__juego", "proceso", "fuente_indirecta",
            "cuenta_costo", "contrapartida",
        ).prefetch_related("asientos").order_by(
            "fuente_indirecta_id", "orden_id", "pk"
        ))

    # ---- Registros y asientos ----
    def registros_de_orden(self, orden):
        return (RegistroCosto.objects.filter(orden=orden)
                .select_related("proceso", "cuenta_costo", "contrapartida")
                .select_related("fuente_indirecta", "periodo_indirecto")
                .prefetch_related("asientos"))

    def obtener_registro(self, registro_id):
        return (RegistroCosto.objects
                .select_related("orden", "orden__juego", "proceso",
                                "cuenta_costo", "contrapartida")
                .filter(pk=registro_id).first())

    def registro_por_clave(self, clave):
        return RegistroCosto.objects.filter(clave_idempotencia=clave).first()

    def crear_registro(self, **datos):
        return RegistroCosto.objects.create(**datos)

    def guardar_registro(self, registro):
        registro.save()
        return registro

    def asiento_por_clave(self, clave):
        return (AsientoCosto.objects.select_related("registro")
                .filter(clave_idempotencia=clave).first())

    def crear_asiento(self, **datos):
        return AsientoCosto.objects.create(**datos)

    def movimientos_de(self, transaccion_id):
        return (Movimiento.objects.filter(transaccion_id=transaccion_id)
                .select_related("cuenta").order_by("id"))
