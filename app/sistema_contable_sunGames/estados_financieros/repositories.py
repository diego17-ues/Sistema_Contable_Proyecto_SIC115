from django.db import DatabaseError
from django.db.models import Count, Q, Sum

from catalogo.models import Cuenta
from libro_mayor.models import (
    EstadoPeriodo,
    Movimiento,
    PeriodoContable,
    TipoMovimiento,
    Transaccion,
)

from .exceptions import GuardadoCierreError, PeriodoNoEncontradoError
from .models import EstadoFinancieroEmitido


class EstadosFinancierosRepository:
    def periodos(self):
        return list(PeriodoContable.objects.order_by("fecha_inicio", "pk"))

    def periodo_mas_reciente(self):
        return PeriodoContable.objects.order_by("-pk").first()

    def obtener_periodo(self, pk):
        try:
            return PeriodoContable.objects.get(pk=pk)
        except (PeriodoContable.DoesNotExist, ValueError, TypeError) as exc:
            raise PeriodoNoEncontradoError() from exc

    def buscar_periodo(self, referencia):
        periodo = PeriodoContable.objects.filter(nombre=referencia).first()
        if periodo is None and str(referencia).isdigit():
            periodo = PeriodoContable.objects.filter(pk=referencia).first()
        if periodo is None:
            raise PeriodoNoEncontradoError()
        return periodo

    def saldos(self, *, hasta, desde=None):
        """Cuentas con movimientos en el rango y su suma firmada."""
        filtro = {"movimientos__fecha__lte": hasta}
        if desde:
            filtro["movimientos__fecha__gte"] = desde
        return list(
            Cuenta.objects.filter(**filtro)
            .select_related("rubro", "subtipo__rubro")
            .annotate(saldo=Sum("movimientos__importe"))
            .order_by("codigo")
        )

    def conteo(self, periodo):
        movimientos = Movimiento.objects.filter(
            fecha__gte=periodo.fecha_inicio, fecha__lte=periodo.fecha_fin
        )
        transacciones = Transaccion.objects.filter(
            movimientos__in=movimientos
        ).distinct().count()
        return transacciones, movimientos.aggregate(n=Count("pk"))["n"]

    def agregados_hoja(self, desde, hasta):
        """Por cuenta: apertura y Debe/Haber del rango, sin y con ajustes."""
        rango = Q(movimientos__fecha__gte=desde, movimientos__fecha__lte=hasta)
        ajuste = Q(movimientos__tipo=TipoMovimiento.AJUSTE)
        debe, haber = Q(movimientos__importe__gt=0), Q(
            movimientos__importe__lt=0
        )
        importe = "movimientos__importe"
        return list(
            Cuenta.objects.filter(movimientos__fecha__lte=hasta).distinct()
            .select_related("rubro", "naturaleza")
            .annotate(
                apertura=Sum(importe, filter=Q(movimientos__fecha__lt=desde)),
                debe=Sum(importe, filter=rango & debe & ~ajuste),
                haber=Sum(importe, filter=rango & haber & ~ajuste),
                ajuste_debe=Sum(importe, filter=rango & debe & ajuste),
                ajuste_haber=Sum(importe, filter=rango & haber & ajuste),
            ).order_by("codigo")
        )

    def ajustes(self, desde, hasta):
        return list(Movimiento.objects.filter(
            tipo=TipoMovimiento.AJUSTE, fecha__gte=desde, fecha__lte=hasta
        ).select_related("cuenta").order_by("fecha", "pk"))

    def periodo_con_rango(self, desde, hasta):
        return PeriodoContable.objects.filter(
            fecha_inicio=desde, fecha_fin=hasta
        ).first()

    def rango_con_cierre(self, desde, hasta):
        return PeriodoContable.objects.filter(
            fecha_inicio__lte=hasta, fecha_fin__gte=desde
        ).exclude(estado=EstadoPeriodo.ABIERTO).exists()

    def nuevo_periodo(self, *, nombre, desde, hasta):
        return PeriodoContable(nombre=nombre, fecha_inicio=desde,
                               fecha_fin=hasta)

    def guardar_periodo(self, periodo):
        return self._guardar(periodo)

    def suma_balanza(self, *, hasta):
        return Movimiento.objects.filter(fecha__lte=hasta).aggregate(
            total=Sum("importe")
        )["total"]

    def ultimo_emitido(self, periodo, tipo):
        return EstadoFinancieroEmitido.objects.filter(
            periodo=periodo, tipo=tipo
        ).select_related("usuario").first()

    def guardar_emitido(self, *, periodo, tipo, datos, usuario):
        return self._guardar(EstadoFinancieroEmitido(
            periodo=periodo, tipo=tipo, datos=datos, usuario=usuario
        ))

    def cerrar(self, periodo):
        periodo.estado = EstadoPeriodo.CIERRE_PROVISIONAL
        return self._guardar(periodo)

    def reabrir(self, periodo):
        periodo.estado = EstadoPeriodo.ABIERTO
        try:
            periodo.save(reapertura=True)
        except DatabaseError as exc:
            raise GuardadoCierreError() from exc
        return periodo

    @staticmethod
    def _guardar(objeto):
        try:
            objeto.save()
        except DatabaseError as exc:
            raise GuardadoCierreError() from exc
        return objeto
