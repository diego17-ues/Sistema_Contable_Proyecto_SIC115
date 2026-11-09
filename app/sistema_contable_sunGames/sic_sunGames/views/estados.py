"""CU-07: cierre provisional, reapertura y PDF de estados financieros."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from estados_financieros.composition import (
    crear_cierre_service,
    crear_estados_financieros_service,
)
from estados_financieros.exceptions import (
    EstadosFinancierosError,
    PeriodoNoEncontradoError,
)
from estados_financieros.forms import (
    AjusteForm,
    CierrePeriodoForm,
    CierreRangoForm,
    RangoForm,
    ReaperturaPeriodoForm,
)
from estados_financieros.models import TipoEstado
from libro_mayor.composition import crear_libro_mayor_service
from libro_mayor.exceptions import LibroMayorError
from libro_mayor.models import TipoMovimiento
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError

from .pages import contexto_panel
from .ventas import verificar_modulo

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


def _rango(datos):
    form = RangoForm(datos)
    if not form.is_valid():
        return None, JsonResponse(
            {"error": "Indica fechas válidas.", "campos": form.errors},
            status=400,
        )
    return form.cleaned_data, None


@login_required
@require_GET
def hoja_trabajo_api(request):
    """CU-07.2 y CU-07.2.1: requisitos del rango y Hoja de Trabajo."""
    if (denegado := verificar_modulo(request, "reports")):
        return denegado
    rango, invalido = _rango(request.GET)
    if invalido:
        return invalido
    desde, hasta = rango["desde"], rango["hasta"]
    estados = crear_estados_financieros_service()
    cierre = crear_cierre_service()
    try:
        hoja = estados.hoja_trabajo(request.user, desde, hasta)
        resumen, cerrado = cierre.requisitos_rango(request.user, desde, hasta)
        cuentas = crear_libro_mayor_service().cuentas(request.user)
    except SIN_PERMISO as error:
        return JsonResponse({"error": str(error)}, status=403)
    except EstadosFinancierosError as error:
        return JsonResponse({"error": str(error)}, status=422)
    periodo = resumen.periodo
    return JsonResponse({
        "worksheet": hoja,
        "estado": "CERRADO_PROVISIONAL" if cerrado else "ABIERTO",
        "periodo": {"id": periodo.pk, "nombre": periodo.nombre,
                    "registrado": periodo.pk is not None},
        "ventasPendientes": resumen.ventas_pendientes,
        "movimientos": resumen.movimientos,
        "transacciones": resumen.transacciones,
        "balanzaCuadra": resumen.cuadra,
        "diferencia": str(resumen.diferencia_absoluta),
        "puedeCerrar": cierre.puede_cerrar(request.user),
        "cuentas": [{"code": c.codigo, "name": c.denominacion,
                     "status": "Activa" if c.activa else "Inactiva"}
                    for c in cuentas],
    })


@login_required
@require_POST
def ajuste_api(request):
    """Ajuste desde la Hoja de Trabajo: se registra en el Libro Mayor."""
    if (denegado := verificar_modulo(request, "reports")):
        return denegado
    form = AjusteForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Revisa los datos del ajuste.",
                             "campos": form.errors}, status=400)
    datos = form.cleaned_data
    try:
        transaccion = crear_libro_mayor_service().registrar(
            request.user, cuenta=datos["code"], movimientos=[{
                "fecha": datos["date"], "concepto": datos["concept"],
                "referencia": datos["reference"],
                "tipo": TipoMovimiento.AJUSTE, "debe": datos["debit"],
                "haber": datos["credit"],
            }],
        )
    except SIN_PERMISO as error:
        return JsonResponse({"error": str(error)}, status=403)
    except LibroMayorError as error:
        return JsonResponse({"error": str(error)}, status=422)
    return JsonResponse({"mensaje": f"Ajuste guardado (transacción "
                                    f"{transaccion.pk})."})


@login_required
@require_POST
def cierre_provisional_api(request):
    if (denegado := verificar_modulo(request, "reports")):
        return denegado
    form = CierreRangoForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Indica fechas válidas.",
                             "campos": form.errors}, status=400)
    datos = form.cleaned_data
    try:
        periodo = crear_cierre_service().cerrar_rango(
            request.user, datos["desde"], datos["hasta"],
            confirmacion=datos["confirmacion"], motivo=datos["motivo"],
        )
    except SIN_PERMISO as error:
        return JsonResponse({"error": str(error)}, status=403)
    except EstadosFinancierosError as error:
        return JsonResponse({"error": str(error), "campo": error.campo},
                            status=422)
    return JsonResponse({"mensaje": f"El período «{periodo.nombre}» quedó "
                                    "cerrado (cierre provisional)."})


@login_required
def estado_pdf_rango(request, tipo):
    contexto_panel(request, "reports")
    if tipo not in TIPOS_PDF:
        raise Http404
    rango, invalido = _rango(request.GET)
    if invalido:
        messages.error(request, "Indica fechas válidas.")
        return redirect("reports")
    try:
        archivo = crear_estados_financieros_service().exportar_pdf_rango(
            request.user, rango["desde"], rango["hasta"], TIPOS_PDF[tipo]
        )
    except SIN_PERMISO as error:
        raise PermissionDenied(str(error)) from error
    except EstadosFinancierosError as error:
        messages.error(request, str(error))
        return redirect("reports")
    respuesta = HttpResponse(archivo.contenido,
                             content_type=archivo.tipo_contenido)
    respuesta["Content-Disposition"] = (
        f'attachment; filename="{archivo.nombre}"'
    )
    return respuesta
