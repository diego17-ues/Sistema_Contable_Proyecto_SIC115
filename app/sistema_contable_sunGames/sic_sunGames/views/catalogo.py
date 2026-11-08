"""CU-06 Catálogo de Cuentas: consulta, registro y modificación."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from catalogo.composition import crear_catalogo_service
from catalogo.exceptions import CatalogoError, CuentaNoEncontradaError
from catalogo.forms import CuentaFiltroForm, CuentaForm
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError

from .pages import contexto_panel

CATALOGO_TEMPLATE = "sic_sunGames/catalogo.html"
REGISTROS_POR_PAGINA = 100
SIN_PERMISO = (RolNoAutorizadoError, UsuarioInactivoError)


def _render(request, servicio, **extra):
    contexto = contexto_panel(request, "accounts")
    try:
        opciones = servicio.opciones(request.user)
        filtro = CuentaFiltroForm(
            request.GET or None, auto_id="filtro_%s", **opciones
        )
        cuentas = []
        if not filtro.is_bound or filtro.is_valid():
            cuentas = servicio.listar(request.user, **filtro.filtros())
    except SIN_PERMISO as error:
        raise PermissionDenied(str(error)) from error
    consulta = request.GET.copy()
    consulta.pop("pagina", None)
    contexto.update(
        filtro=filtro,
        pagina=Paginator(cuentas, REGISTROS_POR_PAGINA).get_page(
            request.GET.get("pagina")
        ),
        consulta=consulta.urlencode(),
        filtrando=bool(consulta),
        puede_modificar=servicio.puede_modificar(request.user),
        sin_subtipos=not opciones["subtipos"],
        **extra,
    )
    return render(request, CATALOGO_TEMPLATE, contexto)


def _formulario(servicio, request, data=None, initial=None):
    return CuentaForm(data, initial=initial, **servicio.opciones(request.user))


def _verificar_escritura(servicio, request):
    try:
        servicio.verificar_escritura(request.user)
    except SIN_PERMISO as error:
        raise PermissionDenied(str(error)) from error


def _valores_actuales(cuenta):
    return {
        "denominacion": cuenta.denominacion,
        "rubro": cuenta.rubro.codigo,
        "subtipo": cuenta.subtipo.prefijo,
        "naturaleza": cuenta.naturaleza.codigo,
    }


@login_required
def cuentas(request):
    return _render(request, crear_catalogo_service())


@login_required
def cuenta_detalle(request, codigo):
    servicio = crear_catalogo_service()
    try:
        ficha = servicio.obtener(request.user, codigo)
    except SIN_PERMISO as error:
        raise PermissionDenied(str(error)) from error
    except CuentaNoEncontradaError as error:
        messages.error(request, str(error))
        return redirect("accounts")
    return _render(request, servicio, ficha=ficha)


@login_required
@require_http_methods(["GET", "POST"])
def cuenta_nueva(request):
    servicio = crear_catalogo_service()
    _verificar_escritura(servicio, request)
    if request.method != "POST":
        return _render(
            request, servicio, form_alta=_formulario(servicio, request)
        )

    form = _formulario(servicio, request, request.POST)
    if form.is_valid():
        try:
            cuenta = servicio.registrar(request.user, form.cleaned_data)
        except SIN_PERMISO as error:
            raise PermissionDenied(str(error)) from error
        except CatalogoError as error:
            form.add_error(error.campo, str(error))
        else:
            messages.success(
                request,
                f"Cuenta {cuenta.codigo} · {cuenta.denominacion} registrada.",
            )
            return redirect("accounts")
    return _render(request, servicio, form_alta=form)


@login_required
@require_http_methods(["GET"])
def cuenta_siguiente_codigo(request):
    """Vista previa del código al elegir tipo y subtipo (CU-06.1)."""
    servicio = crear_catalogo_service()
    try:
        codigo = servicio.siguiente_codigo(
            request.user, request.GET.get("rubro"), request.GET.get("subtipo")
        )
    except SIN_PERMISO as error:
        raise PermissionDenied(str(error)) from error
    except CatalogoError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"codigo": codigo})


@login_required
@require_http_methods(["GET", "POST"])
def cuenta_modificar(request, codigo):
    servicio = crear_catalogo_service()
    _verificar_escritura(servicio, request)
    try:
        cuenta = servicio.obtener(request.user, codigo)
    except CuentaNoEncontradaError as error:
        messages.error(request, str(error))
        return redirect("accounts")

    if request.method != "POST":
        form = _formulario(
            servicio, request, initial=_valores_actuales(cuenta)
        )
        return _render(request, servicio, cuenta=cuenta, form_cambio=form)

    form = _formulario(servicio, request, request.POST)
    if form.is_valid() and "editar" not in request.POST:
        try:
            if "confirmar" not in request.POST:
                revision = servicio.revisar(
                    request.user, codigo, form.cleaned_data
                )
                return _render(
                    request, servicio, cuenta=cuenta, form_cambio=form,
                    revision=revision,
                )
            revision = servicio.modificar(
                request.user, codigo, form.cleaned_data
            )
        except SIN_PERMISO as error:
            raise PermissionDenied(str(error)) from error
        except CatalogoError as error:
            form.add_error(error.campo, str(error))
        else:
            mensaje = f"Cuenta {codigo} modificada."
            if revision.conserva_codigo:
                mensaje += f" La cuenta conserva su código original {codigo}."
            messages.success(request, mensaje)
            return redirect("accounts")
    return _render(request, servicio, cuenta=cuenta, form_cambio=form)
