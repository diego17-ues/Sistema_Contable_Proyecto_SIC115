"""CU-05 Libro Mayor, CU-05.1 Consultar Saldo y Balance de comprobación."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from libro_mayor.composition import crear_libro_mayor_service
from libro_mayor.exceptions import LibroMayorError
from libro_mayor.forms import (
    BalanceComprobacionForm,
    ConsultaMayorForm,
    MovimientoFormSet,
    RegistroMayorForm,
)
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError

from .pages import contexto_panel

LIBRO_MAYOR_TEMPLATE = "sic_sunGames/libro_mayor.html"
SIN_PERMISO = (RolNoAutorizadoError, UsuarioInactivoError)
PREFIJO_MOVIMIENTOS = "mov"
MODO_BALANCE = "trial-balance"


def _sin_permiso(error):
    return PermissionDenied(str(error))


def _asignar_error(error, form):
    campo = error.campo if error.campo in form.fields else None
    form.add_error(campo, str(error))


def _url_mayor(cuenta, desde=None, hasta=None):
    filtros = {"cuenta": cuenta, "desde": desde or "", "hasta": hasta or ""}
    return f"{reverse('ledger')}?{urlencode(filtros)}"


def _consultar(request, servicio, filtro):
    """Detalle de la cuenta y su saldo a la fecha de corte (CU-05.1)."""
    if not filtro.is_valid():
        return None, None
    datos = filtro.cleaned_data
    try:
        consulta = servicio.consultar(
            request.user, datos["cuenta"],
            desde=datos["desde"], hasta=datos["hasta"],
        )
        saldo = servicio.saldo(
            request.user, datos["cuenta"],
            datos["hasta"] or timezone.localdate(),
        )
    except SIN_PERMISO as error:
        raise _sin_permiso(error) from error
    except LibroMayorError as error:
        _asignar_error(error, filtro)
        return None, None
    return consulta, saldo


def _render(request, servicio, filtros, registro=None, formset=None):
    contexto = contexto_panel(request, "ledger")
    try:
        cuentas = servicio.cuentas(request.user)
    except SIN_PERMISO as error:
        raise _sin_permiso(error) from error
    activas = [cuenta for cuenta in cuentas if cuenta.activa]
    filtros = filtros.copy()
    if not filtros.get("cuenta") and activas:
        filtros["cuenta"] = activas[0].codigo
    filtro = ConsultaMayorForm(filtros, cuentas=activas)
    consulta, saldo = _consultar(request, servicio, filtro)
    seleccionada = consulta.cuenta if consulta else next(
        (c for c in activas if c.codigo == filtros.get("cuenta")), None
    )
    contexto.update(
        puede_registrar=servicio.puede_registrar(request.user),
        filtro=filtro,
        cuenta=seleccionada,
        consulta=consulta,
        saldo=saldo,
        registro=registro or RegistroMayorForm(initial={
            "cuenta": filtros.get("cuenta"),
            "desde": filtros.get("desde"), "hasta": filtros.get("hasta"),
        }),
        formset=formset or MovimientoFormSet(prefix=PREFIJO_MOVIMIENTOS),
    )
    return render(request, LIBRO_MAYOR_TEMPLATE, contexto)


def _corte(request):
    form = BalanceComprobacionForm(request.GET if "corte" in request.GET
                                   else None)
    corte = timezone.localdate()
    if form.is_bound and form.is_valid() and form.cleaned_data["corte"]:
        corte = form.cleaned_data["corte"]
    return form, corte


def _balance(request, servicio):
    contexto = contexto_panel(request, "ledger")
    form, corte = _corte(request)
    try:
        balance = servicio.balance_comprobacion(request.user, corte)
    except SIN_PERMISO as error:
        raise _sin_permiso(error) from error
    contexto.update(modo_balance=True, balance_form=form, balance=balance)
    return render(request, LIBRO_MAYOR_TEMPLATE, contexto)


@login_required
def libro_mayor(request):
    servicio = crear_libro_mayor_service()
    if request.GET.get("mode") == MODO_BALANCE:
        return _balance(request, servicio)
    return _render(request, servicio, request.GET)


@login_required
def balance_pdf(request):
    servicio = crear_libro_mayor_service()
    _, corte = _corte(request)
    try:
        archivo = servicio.exportar_balance(request.user, corte)
    except SIN_PERMISO as error:
        raise _sin_permiso(error) from error
    respuesta = HttpResponse(
        archivo.contenido, content_type=archivo.tipo_contenido
    )
    respuesta["Content-Disposition"] = (
        f'attachment; filename="{archivo.nombre}"'
    )
    return respuesta


@login_required
@require_POST
def registrar_transaccion(request):
    servicio = crear_libro_mayor_service()
    try:
        servicio.verificar_registro(request.user)
    except SIN_PERMISO as error:
        raise _sin_permiso(error) from error
    registro = RegistroMayorForm(request.POST)
    formset = MovimientoFormSet(request.POST, prefix=PREFIJO_MOVIMIENTOS)
    filtros = {
        clave: request.POST.get(clave, "")
        for clave in ("cuenta", "desde", "hasta")
    }
    if registro.is_valid() and formset.is_valid():
        lineas = [fila.cleaned_data for fila in formset.forms]
        try:
            servicio.registrar(
                request.user, cuenta=registro.cleaned_data["cuenta"],
                movimientos=lineas,
            )
        except SIN_PERMISO as error:
            raise _sin_permiso(error) from error
        except LibroMayorError as error:
            if error.linea is not None:
                _asignar_error(error, formset.forms[error.linea])
            else:
                registro.add_error(None, str(error))
        else:
            messages.success(
                request,
                f"{len(lineas)} movimiento(s) registrado(s) en el Libro "
                "Mayor.",
            )
            return redirect(_url_mayor(**filtros))
    return _render(request, servicio, filtros, registro, formset)
