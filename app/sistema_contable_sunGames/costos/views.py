"""Vistas del módulo de costos (órdenes de trabajo).

Presentación delgada: valida con formularios y delega en servicios.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from sic_sunGames.views.pages import contexto_panel
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError

from .composition import (
    crear_catalogo_costos_service,
    crear_orden_service,
    crear_registro_service,
)
from .exceptions import CostosError
from .forms import (
    AnularForm,
    ConfiguracionCuentaForm,
    CostoForm,
    EstimacionRefForm,
    FiltroOrdenForm,
    LicenciasForm,
    ManoObraForm,
    OrdenForm,
    ProcesoEditForm,
    ProcesoForm,
)
from .models import Elemento

ORDENES_TEMPLATE = "costos/ordenes.html"
ORDEN_TEMPLATE = "costos/orden.html"
CATALOGOS_TEMPLATE = "costos/catalogos.html"
REGISTROS_POR_PAGINA = 50
SIN_PERMISO = (RolNoAutorizadoError, UsuarioInactivoError)
ELEMENTOS_URL = {
    "mano-obra": Elemento.MANO_OBRA,
    "directo": Elemento.DIRECTO,
    "indirecto": Elemento.INDIRECTO,
}


def _sin_permiso(error):
    raise PermissionDenied(str(error)) from error


def _error_en_form(form, error):
    campo = getattr(error, "campo", None)
    form.add_error(campo if campo in form.fields else None, str(error))


def _contexto(request, screen="costos"):
    return contexto_panel(request, screen)


def _int(valor):
    return int(valor) if valor else None


# ---------------------------------------------------------------- órdenes

def _render_ordenes(request, form_nueva=None):
    servicio = crear_orden_service()
    filtro = FiltroOrdenForm(request.GET or None)
    estado = filtro["estado"].value() if filtro.is_valid() else None
    try:
        lista = servicio.listar(request.user, estado=estado or None)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    contexto = _contexto(request)
    contexto.update(
        filtro=filtro, estado=estado or "", form_nueva=form_nueva,
        pagina=Paginator(lista, REGISTROS_POR_PAGINA).get_page(
            request.GET.get("pagina")
        ),
    )
    return render(request, ORDENES_TEMPLATE, contexto)


@login_required
def ordenes(request):
    return _render_ordenes(request)


@login_required
@require_http_methods(["GET", "POST"])
def orden_nueva(request):
    if request.method != "POST":
        return _render_ordenes(request, OrdenForm())
    form = OrdenForm(request.POST)
    if form.is_valid():
        try:
            orden = crear_orden_service().crear_orden(
                request.user,
                nombre_juego=form.cleaned_data["nombre_juego"],
                fecha_inicio=form.cleaned_data["fecha_inicio"],
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(request, "Orden de trabajo creada.")
            return redirect("costos_orden", orden_id=orden.pk)
    return _render_ordenes(request, form)


def _render_orden(request, orden_id, **modal):
    servicio = crear_orden_service()
    registro_service = crear_registro_service()
    try:
        orden, secciones, resumen = servicio.hoja_costos(
            request.user, orden_id
        )
        configuradas = registro_service.configuraciones_disponibles(
            request.user
        )
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.error(request, str(error))
        return redirect("costos_ordenes")
    contexto = _contexto(request)
    contexto.update(
        orden=orden, secciones=secciones, resumen=resumen,
        bloqueados=[e.label for e in Elemento if e not in configuradas],
        **modal,
    )
    return render(request, ORDEN_TEMPLATE, contexto)


@login_required
def orden_detalle(request, orden_id):
    return _render_orden(request, orden_id)


@login_required
@require_http_methods(["GET", "POST"])
def orden_licencias(request, orden_id):
    form = LicenciasForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            crear_orden_service().actualizar_licencias(
                request.user, orden_id,
                form.cleaned_data["licencias_estimadas"],
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(request, "Licencias estimadas actualizadas.")
            return redirect("costos_orden", orden_id=orden_id)
    return _render_orden(request, orden_id, form_licencias=form)


@login_required
@require_http_methods(["GET", "POST"])
def orden_estimacion(request, orden_id):
    servicio = crear_orden_service()
    try:
        versiones = servicio.versiones_aprobadas(request.user)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    try:
        actual = servicio.detalle(request.user, orden_id).estimacion_ref_id
    except CostosError as error:
        messages.error(request, str(error))
        return redirect("costos_ordenes")
    form = EstimacionRefForm(
        request.POST if request.method == "POST" else None,
        initial={"version": actual or ""}, versiones=versiones,
    )
    if request.method == "POST" and form.is_valid():
        try:
            servicio.vincular_estimacion(
                request.user, orden_id, _int(form.cleaned_data["version"])
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(request, "Estimación de referencia guardada.")
            return redirect("costos_orden", orden_id=orden_id)
    return _render_orden(request, orden_id, form_estimacion=form)


# ------------------------------------------------------------- registros

@login_required
@require_http_methods(["GET", "POST"])
def registro_nuevo(request, orden_id, tipo):
    elemento = ELEMENTOS_URL.get(tipo)
    if elemento is None:
        return redirect("costos_orden", orden_id=orden_id)
    servicio = crear_registro_service()
    try:
        configuracion = servicio.configuracion(request.user, elemento)
        procesos = servicio.procesos(request.user)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.error(request, str(error))
        return redirect("costos_orden", orden_id=orden_id)
    clase = ManoObraForm if elemento == Elemento.MANO_OBRA else CostoForm
    form = clase(request.POST if request.method == "POST" else None,
                 procesos=procesos, configuracion=configuracion)
    if request.method == "POST" and form.is_valid():
        try:
            _registrar(servicio, request.user, orden_id, elemento,
                       form.cleaned_data)
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(request, "Registro guardado y asentado en el "
                                      "Libro Mayor.")
            return redirect("costos_orden", orden_id=orden_id)
    return _render_orden(
        request, orden_id, form_registro=form, tipo_registro=tipo,
        elemento_registro=elemento.label, configuracion=configuracion,
    )


def _registrar(servicio, actor, orden_id, elemento, datos):
    comunes = dict(
        orden_id=orden_id, fecha=datos["fecha"],
        proceso_id=_int(datos["proceso"]),
        contrapartida_id=_int(datos["contrapartida"]), clave=datos["clave"],
    )
    if elemento == Elemento.MANO_OBRA:
        return servicio.registrar_mano_obra(
            actor, horas=datos["horas"], costo_hora=datos["costo_hora"],
            **comunes,
        )
    return servicio.registrar_costo(
        actor, elemento=elemento, descripcion=datos["descripcion"],
        importe=datos["importe"], **comunes,
    )


@login_required
@require_http_methods(["GET", "POST"])
def registro_anular(request, orden_id, registro_id):
    servicio = crear_registro_service()
    try:
        registro, lineas = servicio.vista_previa_anulacion(
            request.user, registro_id
        )
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.error(request, str(error))
        return redirect("costos_orden", orden_id=orden_id)
    form = AnularForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            servicio.anular(request.user, registro_id=registro.pk,
                            motivo=form.cleaned_data["motivo"],
                            clave=form.cleaned_data["clave"])
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(request, "Registro anulado con su "
                                      "contra-asiento.")
            return redirect("costos_orden", orden_id=registro.orden_id)
    return _render_orden(
        request, registro.orden_id, form_anular=form,
        registro_anular=registro, lineas_anulacion=lineas,
    )


# ------------------------------------------------------------- catálogos

def _render_catalogos(request, **extra):
    servicio = crear_catalogo_costos_service()
    try:
        procesos = servicio.procesos(request.user)
        configuraciones = servicio.configuraciones(request.user)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    contexto = _contexto(request)
    contexto.update(
        procesos=procesos,
        elementos=[(e.value, e.label, configuraciones.get(e.value))
                   for e in Elemento],
        **extra,
    )
    return render(request, CATALOGOS_TEMPLATE, contexto)


@login_required
def catalogos(request):
    return _render_catalogos(request)


@login_required
@require_http_methods(["GET", "POST"])
def proceso_nuevo(request):
    form = ProcesoForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            crear_catalogo_costos_service().crear_proceso(
                request.user, **form.cleaned_data
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(request, "Proceso registrado.")
            return redirect("costos_catalogos")
    return _render_catalogos(request, form_proceso=form)


@login_required
@require_POST
def proceso_editar(request, proceso_id):
    form = ProcesoEditForm(request.POST)
    if form.is_valid():
        try:
            crear_catalogo_costos_service().actualizar_proceso(
                request.user, proceso_id, **form.cleaned_data
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Proceso actualizado.")
    else:
        messages.error(request, "Revisa el costo por hora del proceso.")
    return redirect("costos_catalogos")


@login_required
@require_http_methods(["GET", "POST"])
def configuracion_editar(request, elemento):
    if elemento not in Elemento.values:
        return redirect("costos_catalogos")
    servicio = crear_catalogo_costos_service()
    try:
        cuentas = servicio.cuentas(request.user)
        actual = servicio.configuraciones(request.user).get(elemento)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    inicial = None
    if actual is not None:
        inicial = {
            "cuenta_costo": str(actual.cuenta_costo_id),
            "contrapartidas": [str(c.pk)
                               for c in actual.contrapartidas.all()],
            "contrapartida_defecto": str(actual.contrapartida_defecto_id),
        }
    form = ConfiguracionCuentaForm(
        request.POST if request.method == "POST" else None,
        initial=inicial, cuentas=cuentas,
    )
    if request.method == "POST" and form.is_valid():
        cuenta_costo, contrapartidas, defecto = form.cuentas_elegidas()
        try:
            servicio.guardar_configuracion(
                request.user, elemento=elemento, cuenta_costo=cuenta_costo,
                contrapartidas=contrapartidas,
                contrapartida_defecto=defecto,
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(request, "Configuración de cuentas guardada.")
            return redirect("costos_catalogos")
    return _render_catalogos(request, form_config=form,
                             elemento_config=Elemento(elemento))
