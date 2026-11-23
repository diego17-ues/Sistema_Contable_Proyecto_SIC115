from decimal import Decimal

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q, Sum

from libro_mayor.models import Movimiento

from .exceptions import (
    ContabilizacionError,
    VentaDuplicadaError,
    VentaNoEncontradaError,
)
from .models import (
    ConciliacionVentas,
    ConexionSteam,
    EstadoVenta,
    OrigenVenta,
    Venta,
)


def _rango_fecha_hora(desde, hasta):
    filtro = Q()
    if desde:
        filtro &= Q(fecha_hora__date__gte=desde)
    if hasta:
        filtro &= Q(fecha_hora__date__lte=hasta)
    return filtro


class VentaRepository:
    def existe(self, identificador):
        return Venta.objects.filter(identificador=identificador).exists()

    def crear(self, **datos):
        try:
            with transaction.atomic():
                return Venta.objects.create(**datos)
        except IntegrityError as exc:
            raise VentaDuplicadaError() from exc

    def listar(self, *, consulta="", desde=None, hasta=None):
        ventas = Venta.objects.filter(_rango_fecha_hora(desde, hasta))
        if consulta:
            ventas = ventas.filter(
                Q(identificador__icontains=consulta)
                | Q(titulo__icontains=consulta)
            )
        return list(ventas)

    def ventas_en_periodo(self, desde, hasta):
        return list(Venta.objects.filter(
            _rango_fecha_hora(desde, hasta)
        ).order_by("fecha_hora", "pk"))

    def obtener(self, identificador):
        try:
            return Venta.objects.get(identificador=identificador)
        except Venta.DoesNotExist as exc:
            raise VentaNoEncontradaError() from exc

    def contar_pendientes(self, desde, hasta):
        return Venta.objects.filter(
            _rango_fecha_hora(desde, hasta), estado=EstadoVenta.PENDIENTE
        ).count()

    def hubo_venta_real(self, desde, hasta):
        return Venta.objects.filter(
            origen=OrigenVenta.REAL,
            fecha_recepcion__gte=desde,
            fecha_recepcion__lte=hasta,
        ).exists()

    def bloquear_conciliacion(self):
        """Serializa las conciliaciones concurrentes (fila única)."""
        ConexionSteam.objects.get_or_create(pk=1)
        ConexionSteam.objects.select_for_update().get(pk=1)

    def conciliacion_que_se_solapa(self, desde, hasta):
        return ConciliacionVentas.objects.filter(
            desde__lte=hasta, hasta__gte=desde
        ).order_by("desde").first()

    def crear_conciliacion(self, **datos):
        try:
            return ConciliacionVentas.objects.create(**datos)
        except DatabaseError as exc:
            raise ContabilizacionError() from exc

    def importe_por_cobrar(self, venta, codigo_cuenta):
        if not venta.transaccion_id:
            return venta.neto
        return Movimiento.objects.filter(
            transaccion_id=venta.transaccion_id,
            cuenta__codigo=codigo_cuenta,
        ).aggregate(t=Sum("importe"))["t"] or Decimal("0.00")

    def marcar_cobrada(self, venta, transaccion_mayor):
        venta.transaccion_cobro = transaccion_mayor
        try:
            venta.save(update_fields=["transaccion_cobro"])
        except DatabaseError as exc:
            raise ContabilizacionError() from exc

    def marcar_registrada(self, venta, transaccion_mayor):
        venta.estado = EstadoVenta.REGISTRADA
        venta.transaccion = transaccion_mayor
        try:
            venta.save(update_fields=["estado", "transaccion"])
        except DatabaseError as exc:
            raise ContabilizacionError() from exc
        return venta

    def registrar_contacto(self, momento):
        conexion, _ = ConexionSteam.objects.get_or_create(pk=1)
        conexion.ultimo_contacto = momento
        conexion.ultimo_error = None
        conexion.save(update_fields=["ultimo_contacto", "ultimo_error"])

    def registrar_error(self, momento):
        conexion, _ = ConexionSteam.objects.get_or_create(pk=1)
        conexion.ultimo_error = momento
        conexion.save(update_fields=["ultimo_error"])

    def ultimo_contacto(self):
        return ConexionSteam.objects.filter(pk=1).values_list(
            "ultimo_contacto", flat=True
        ).first()

    def ultimo_error(self):
        return ConexionSteam.objects.filter(pk=1).values_list(
            "ultimo_error", flat=True
        ).first()
