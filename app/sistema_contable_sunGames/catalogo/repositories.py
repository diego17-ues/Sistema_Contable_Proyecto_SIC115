from functools import wraps

from django.db import DatabaseError, IntegrityError, transaction

from .exceptions import (
    CuentaDuplicadaError,
    CuentaNoEncontradaError,
    GuardadoCuentaError,
    NaturalezaInvalidaError,
    RubroInvalidoError,
    SubtipoInvalidoError,
)
from .models import (
    AprobacionCuenta,
    Cuenta,
    HistorialCuenta,
    Naturaleza,
    Rubro,
    Subtipo,
)


def _traducir_errores_de_guardado(metodo):
    @wraps(metodo)
    def envoltura(self, *args, **kwargs):
        try:
            with transaction.atomic():
                return metodo(self, *args, **kwargs)
        except IntegrityError as exc:
            if "denominacion_normalizada" in str(exc):
                raise CuentaDuplicadaError() from exc
            raise GuardadoCuentaError() from exc
        except DatabaseError as exc:
            raise GuardadoCuentaError() from exc
    return envoltura


class CuentaRepository:
    def listar(self, *, codigo="", denominacion="", rubro="", naturaleza="",
               activa=None):
        cuentas = Cuenta.objects.select_related(
            "rubro", "subtipo__rubro", "naturaleza"
        )
        if codigo:
            cuentas = cuentas.filter(codigo__startswith=codigo)
        if denominacion:
            cuentas = cuentas.filter(denominacion__icontains=denominacion)
        if rubro:
            cuentas = cuentas.filter(rubro__codigo=rubro)
        if naturaleza:
            cuentas = cuentas.filter(naturaleza__codigo=naturaleza)
        if activa is not None:
            cuentas = cuentas.filter(activa=activa)
        return cuentas.order_by("codigo")

    def obtener_por_codigo(self, codigo):
        try:
            return Cuenta.objects.select_related(
                "rubro", "subtipo__rubro", "naturaleza"
            ).get(codigo=codigo)
        except Cuenta.DoesNotExist as exc:
            raise CuentaNoEncontradaError() from exc

    def existe_denominacion(self, normalizada, *, excluir_codigo=None):
        cuentas = Cuenta.objects.filter(denominacion_normalizada=normalizada)
        if excluir_codigo:
            cuentas = cuentas.exclude(codigo=excluir_codigo)
        return cuentas.exists()

    def rubros(self):
        return Rubro.objects.order_by("codigo")

    def subtipos(self):
        return Subtipo.objects.select_related("rubro").order_by(
            "rubro__codigo", "codigo"
        )

    def naturalezas(self):
        return Naturaleza.objects.order_by("nombre")

    def obtener_rubro(self, codigo):
        try:
            return Rubro.objects.get(codigo=codigo)
        except Rubro.DoesNotExist as exc:
            raise RubroInvalidoError() from exc

    def obtener_subtipo(self, rubro, codigo):
        try:
            return Subtipo.objects.select_related("rubro").get(
                rubro=rubro, codigo=codigo
            )
        except Subtipo.DoesNotExist as exc:
            raise SubtipoInvalidoError() from exc

    def obtener_naturaleza(self, codigo):
        try:
            return Naturaleza.objects.get(codigo=codigo)
        except Naturaleza.DoesNotExist as exc:
            raise NaturalezaInvalidaError() from exc

    def bloquear_subtipo(self, subtipo):
        """Serializa la asignación de códigos dentro del mismo subtipo."""
        return Subtipo.objects.select_for_update().get(pk=subtipo.pk)

    def codigos_con_prefijo(self, prefijo):
        """Códigos usados en el subtipo, activos o dados de baja."""
        return list(
            Cuenta.objects.filter(codigo__startswith=prefijo)
            .values_list("codigo", flat=True)
        )

    def nueva(self, **campos):
        return Cuenta(**campos)

    @_traducir_errores_de_guardado
    def guardar(self, cuenta):
        cuenta.save()
        return cuenta

    @_traducir_errores_de_guardado
    def registrar_aprobacion(self, cuenta, *, tipo, usuario, documentacion,
                             cambios=()):
        aprobacion = AprobacionCuenta.objects.create(
            cuenta=cuenta, tipo=tipo, usuario=usuario, **documentacion
        )
        HistorialCuenta.objects.bulk_create(
            HistorialCuenta(
                aprobacion=aprobacion, campo=cambio.campo,
                valor_anterior=cambio.anterior, valor_nuevo=cambio.nuevo,
            )
            for cambio in cambios
        )
        return aprobacion
