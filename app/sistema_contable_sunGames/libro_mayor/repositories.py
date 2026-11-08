from django.db import DatabaseError, transaction
from django.db.models import Q, Sum

from catalogo.models import Cuenta

from .exceptions import (
    CuentaNoRegistrableError,
    FechaInvalidaError,
    GuardadoTransaccionError,
)
from .models import Movimiento, PeriodoContable, Transaccion


class TransaccionRepository:
    def periodo_de(self, fecha):
        periodo = PeriodoContable.objects.filter(
            fecha_inicio__lte=fecha, fecha_fin__gte=fecha
        ).first()
        if periodo is None:
            raise FechaInvalidaError(campo="fecha")
        return periodo

    def cuentas(self):
        return Cuenta.objects.select_related("naturaleza").order_by("codigo")

    def obtener_cuenta(self, codigo):
        try:
            return Cuenta.objects.select_related("naturaleza").get(
                codigo=codigo
            )
        except Cuenta.DoesNotExist as exc:
            raise CuentaNoRegistrableError(
                "La cuenta no existe en el catálogo.", campo="cuenta"
            ) from exc

    def tiene_subcuentas(self, cuenta):
        return Cuenta.objects.filter(
            codigo__startswith=cuenta.codigo
        ).exclude(pk=cuenta.pk).exists()

    def crear_transaccion(self, *, fecha, concepto, usuario):
        return self._guardar(
            Transaccion(fecha=fecha, concepto=concepto, usuario=usuario)
        )

    def crear_movimiento(self, *, transaccion, cuenta, importe):
        return self._guardar(
            Movimiento(transaccion=transaccion, cuenta=cuenta, importe=importe)
        )

    def movimientos(self, cuenta, *, desde=None, hasta=None):
        movimientos = Movimiento.objects.select_related("transaccion").filter(
            cuenta=cuenta
        )
        if desde:
            movimientos = movimientos.filter(transaccion__fecha__gte=desde)
        if hasta:
            movimientos = movimientos.filter(transaccion__fecha__lte=hasta)
        return movimientos.order_by("transaccion__fecha", "transaccion_id")

    def totales(self, cuenta, *, hasta=None, antes_de=None):
        """Suma de cargos (positivos) y abonos (negativos) de la cuenta."""
        movimientos = Movimiento.objects.filter(cuenta=cuenta)
        if hasta:
            movimientos = movimientos.filter(transaccion__fecha__lte=hasta)
        if antes_de:
            movimientos = movimientos.filter(transaccion__fecha__lt=antes_de)
        return movimientos.aggregate(
            cargos=Sum("importe", filter=Q(importe__gt=0)),
            abonos=Sum("importe", filter=Q(importe__lt=0)),
        )

    @staticmethod
    def _guardar(objeto):
        try:
            with transaction.atomic():
                objeto.save()
        except DatabaseError as exc:
            raise GuardadoTransaccionError() from exc
        return objeto
