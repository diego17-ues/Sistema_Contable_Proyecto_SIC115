from django.db import DatabaseError, transaction
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import ExtractYear

from catalogo.models import Cuenta

from .exceptions import (
    CuentaNoRegistrableError,
    FechaInvalidaError,
    GuardadoTransaccionError,
)
from .models import EstadoPeriodo, Movimiento, PeriodoContable, Transaccion


class TransaccionRepository:
    def periodo_de(self, fecha):
        periodos = PeriodoContable.objects.que_contienen(fecha)
        periodo = (
            periodos.exclude(estado=EstadoPeriodo.ABIERTO).first()
            or periodos.first()
        )
        if periodo is None:
            raise FechaInvalidaError(campo="fecha")
        return periodo

    def cuentas(self):
        return Cuenta.objects.select_related(
            "naturaleza", "rubro", "subtipo"
        ).order_by("codigo")

    def obtener_cuenta(self, codigo):
        try:
            return Cuenta.objects.select_related(
                "naturaleza", "rubro", "subtipo"
            ).get(codigo=codigo)
        except Cuenta.DoesNotExist as exc:
            raise CuentaNoRegistrableError(
                "La cuenta no existe en el catálogo.", campo="cuenta"
            ) from exc

    def tiene_subcuentas(self, cuenta):
        return Cuenta.objects.filter(
            codigo__startswith=cuenta.codigo
        ).exclude(pk=cuenta.pk).exists()

    def crear_transaccion(self, *, usuario):
        return self._guardar(Transaccion(usuario=usuario))

    def crear_movimiento(self, *, transaccion, cuenta, fecha, concepto,
                         referencia, tipo, importe):
        return self._guardar(Movimiento(
            transaccion=transaccion, cuenta=cuenta, fecha=fecha,
            concepto=concepto, referencia=referencia, tipo=tipo,
            importe=importe,
        ))

    def movimientos(self, cuenta, *, desde=None, hasta=None):
        """Movimientos de la cuenta con su número dentro del tipo y año."""
        anteriores = Movimiento.objects.filter(
            tipo=OuterRef("tipo"), fecha__year=OuterRef("anio"),
            pk__lte=OuterRef("pk"),
        ).order_by().values("tipo").annotate(n=Count("pk")).values("n")
        movimientos = Movimiento.objects.filter(cuenta=cuenta)
        if desde:
            movimientos = movimientos.filter(fecha__gte=desde)
        if hasta:
            movimientos = movimientos.filter(fecha__lte=hasta)
        return movimientos.annotate(
            anio=ExtractYear("fecha"),
            numero=Subquery(anteriores, output_field=IntegerField()),
        ).order_by("fecha", "pk")

    def totales(self, cuenta, *, hasta=None, antes_de=None):
        """Suma del Debe (positivos) y del Haber (negativos) de la cuenta."""
        movimientos = Movimiento.objects.filter(cuenta=cuenta)
        if hasta:
            movimientos = movimientos.filter(fecha__lte=hasta)
        if antes_de:
            movimientos = movimientos.filter(fecha__lt=antes_de)
        return movimientos.aggregate(
            cargos=Sum("importe", filter=Q(importe__gt=0)),
            abonos=Sum("importe", filter=Q(importe__lt=0)),
        )

    def saldos_por_cuenta(self, *, hasta):
        """Solo las cuentas con movimientos hasta la fecha, con su suma."""
        return Cuenta.objects.filter(
            movimientos__fecha__lte=hasta
        ).annotate(saldo=Sum("movimientos__importe")).order_by("codigo")

    @staticmethod
    def _guardar(objeto):
        try:
            with transaction.atomic():
                objeto.save()
        except DatabaseError as exc:
            raise GuardadoTransaccionError() from exc
        return objeto
