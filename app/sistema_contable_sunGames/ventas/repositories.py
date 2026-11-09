from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q

from .exceptions import (
    ContabilizacionError,
    VentaDuplicadaError,
    VentaNoEncontradaError,
)
from .models import ConexionSteam, EstadoVenta, Venta


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
