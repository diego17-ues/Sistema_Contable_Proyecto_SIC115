"""Repositorio del subsistema de costos: encapsula el acceso al ORM."""

from django.db.models import Q, Sum

from catalogo.models import Cuenta
from libro_mayor.models import Movimiento

from .models import (
    AsientoCosto,
    ConfiguracionCuentaCosto,
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

    def ordenes(self, *, estado=None):
        qs = OrdenTrabajo.objects.select_related("juego").annotate(
            total_vigente=Sum(
                "registros__importe",
                filter=Q(registros__estado=RegistroCosto.ESTADO_VIGENTE),
            )
        )
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def obtener_orden(self, orden_id):
        return (OrdenTrabajo.objects.select_related("juego")
                .filter(pk=orden_id).first())

    def orden_por_juego(self, juego):
        return OrdenTrabajo.objects.filter(juego=juego).first()

    def crear_orden(self, *, juego, fecha_inicio, usuario):
        return OrdenTrabajo.objects.create(
            juego=juego, fecha_inicio=fecha_inicio, creado_por=usuario,
        )

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
        return Cuenta.objects.filter(activa=True).order_by("codigo")

    def obtener_cuenta(self, cuenta_id):
        return Cuenta.objects.filter(pk=cuenta_id).first()

    # ---- Registros y asientos ----
    def registros_de_orden(self, orden):
        return (RegistroCosto.objects.filter(orden=orden)
                .select_related("proceso", "cuenta_costo", "contrapartida")
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
