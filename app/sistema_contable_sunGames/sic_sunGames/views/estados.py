"""CU-07: cierre provisional, reapertura y PDF de estados financieros."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from estados_financieros.composition import (
    crear_cierre_service,
    crear_estados_financieros_service,
)
from estados_financieros.exceptions import (
    EstadosFinancierosError,
    PeriodoNoEncontradoError,
)
from estados_financieros.forms import CierrePeriodoForm, ReaperturaPeriodoForm
from estados_financieros.models import TipoEstado
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError

from .pages import contexto_panel

TEMPLATE = "sic_sunGames/cierre_periodos.html"
SIN_PERMISO = (RolNoAutorizadoError, UsuarioInactivoError)
TIPOS_PDF = {
    "balance-general": TipoEstado.BALANCE_GENERAL,
    "estado-resultados": TipoEstado.ESTADO_RESULTADOS,
}


def _prefijo(periodo_id):
    return f"p{periodo_id}"


def _render(request, servicio, *, accion=None, periodo_id=None, form=None):
    contexto = contexto_panel(request, "reports")
    try:
        resumenes = servicio.resumenes(request.user)
    except SIN_PERMISO as error:
        raise PermissionDenied(str(error)) from error
    filas = []
    for resumen in resumenes:
        pk = resumen.periodo.pk
        con_error = form is not None and pk == periodo_id
        filas.append({
            "resumen": resumen,
            "form_cierre": form if con_error and accion == "cerrar"
            else CierrePeriodoForm(prefix=_prefijo(pk)),
            "form_reapertura": form if con_error and accion == "reabrir"
            else ReaperturaPeriodoForm(prefix=_prefijo(pk)),
            "abrir": accion if con_error else None,
        })
    contexto.update(
        filas=filas,
        puede_cerrar=servicio.puede_cerrar(request.user),
        puede_reabrir=servicio.puede_reabrir(request.user),
    )
    return render(request, TEMPLATE, contexto,
                  status=400 if form is not None else 200)


def _asignar_error(form, error):
    campo = error.campo if error.campo in form.fields else None
    form.add_error(campo, str(error))


@login_required
def cierre_periodos(request):
    return _render(request, crear_cierre_service())


@login_required
@require_POST
def cerrar_periodo(request, periodo_id):
    contexto_panel(request, "reports")
    servicio = crear_cierre_service()
    form = CierrePeriodoForm(request.POST, prefix=_prefijo(periodo_id))
    if form.is_valid():
        try:
            periodo = servicio.cerrar(request.user, periodo_id,
                                      **form.cleaned_data)
        except SIN_PERMISO as error:
            raise PermissionDenied(str(error)) from error
        except PeriodoNoEncontradoError as error:
            raise Http404(str(error)) from error
        except EstadosFinancierosError as error:
            _asignar_error(form, error)
        else:
            messages.success(
                request, f"El período «{periodo.nombre}» quedó cerrado "
                         "(cierre provisional)."
            )
            return redirect("cierre_periodos")
    return _render(request, servicio, accion="cerrar", periodo_id=periodo_id,
                   form=form)


@login_required
@require_POST
def reabrir_periodo(request, periodo_id):
    contexto_panel(request, "reports")
    servicio = crear_cierre_service()
    try:
        if not servicio.puede_reabrir(request.user):
            servicio.registrar_reapertura_denegada(request.user, periodo_id)
            raise PermissionDenied(
                "Solo un administrador puede reabrir un período."
            )
    except PeriodoNoEncontradoError as error:
        raise Http404(str(error)) from error
    form = ReaperturaPeriodoForm(request.POST, prefix=_prefijo(periodo_id))
    if form.is_valid():
        try:
            periodo = servicio.reabrir(request.user, periodo_id,
                                       **form.cleaned_data)
        except SIN_PERMISO as error:
            raise PermissionDenied(str(error)) from error
        except PeriodoNoEncontradoError as error:
            raise Http404(str(error)) from error
        except EstadosFinancierosError as error:
            _asignar_error(form, error)
        else:
            messages.success(request,
                             f"El período «{periodo.nombre}» está abierto.")
            return redirect("cierre_periodos")
    return _render(request, servicio, accion="reabrir",
                   periodo_id=periodo_id, form=form)


@login_required
def estado_pdf(request, periodo_id, tipo):
    contexto_panel(request, "reports")
    if tipo not in TIPOS_PDF:
        raise Http404
    servicio = crear_estados_financieros_service()
    try:
        archivo = servicio.exportar_pdf(request.user, periodo_id,
                                        TIPOS_PDF[tipo])
    except SIN_PERMISO as error:
        raise PermissionDenied(str(error)) from error
    except PeriodoNoEncontradoError as error:
        raise Http404(str(error)) from error
    except EstadosFinancierosError as error:
        messages.error(request, str(error))
        return redirect("cierre_periodos")
    respuesta = HttpResponse(archivo.contenido,
                             content_type=archivo.tipo_contenido)
    respuesta["Content-Disposition"] = (
        f'attachment; filename="{archivo.nombre}"'
    )
    return respuesta
