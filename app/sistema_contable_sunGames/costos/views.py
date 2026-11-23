"""Vistas del módulo de costos (órdenes de trabajo).

Presentación delgada: valida con formularios y delega en servicios.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from sic_sunGames.views.pages import contexto_panel
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError

from .composition import (
    crear_aplicacion_indirectos_service,
    crear_catalogo_costos_service,
    crear_orden_service,
    crear_registro_service,
)
from .exceptions import CostosError
from .forms import (
    AmortizacionForm,
    AplicarIndirectosForm,
    AnularForm,
    ConfiguracionCuentaForm,
    CostoForm,
    ConfirmarBajaForm,
    ConfirmarCambioForm,
    ExcluirCuentaIndirectaForm,
    EstimacionRefForm,
    FiltroOrdenForm,
    FuenteIndirectaForm,
    LicenciasForm,
    ManoObraForm,
    OrdenEdicionForm,
    OrdenForm,
    PeriodoIndirectoForm,
    ProcesoEditForm,
    ProcesoForm,
    RevertirIndirectosForm,
)
from .models import Elemento

ORDENES_TEMPLATE = "costos/ordenes.html"
ORDEN_TEMPLATE = "costos/orden.html"
CATALOGOS_TEMPLATE = "costos/catalogos.html"
INDIRECTOS_TEMPLATE = "costos/indirectos_periodo.html"
RENDIMIENTO_TEMPLATE = "costos/rendimiento.html"
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
        archivadas = estado == "ELIMINADA"
        lista = servicio.listar(
            request.user,
            estado=None if archivadas else (estado or None),
            incluir_eliminadas=archivadas,
        )
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
    servicio = crear_orden_service()
    try:
        estimaciones = servicio.versiones_disponibles(request.user)
    except SIN_PERMISO as error:
        _sin_permiso(error)

    if request.method != "POST":
        return _render_ordenes(
            request, OrdenForm(estimaciones=estimaciones)
        )
    form = OrdenForm(request.POST, estimaciones=estimaciones)
    if form.is_valid():
        try:
            orden = servicio.crear_orden(
                request.user,
                nombre_juego=form.cleaned_data["nombre_juego"],
                fecha_inicio=form.cleaned_data["fecha_inicio"],
                estimacion_id=_int(form.cleaned_data["estimacion"]),
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
@require_POST
def orden_finalizar(request, orden_id):
    try:
        crear_orden_service().finalizar(request.user, orden_id)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request, "Orden finalizada; sus costos pasaron a videojuegos "
            "terminados (1107)."
        )
    return redirect("costos_orden", orden_id=orden_id)


@login_required
@require_http_methods(["GET", "POST"])
def orden_editar(request, orden_id):
    servicio = crear_orden_service()
    try:
        orden = servicio.detalle(request.user, orden_id)
        versiones = servicio.versiones_disponibles(
            request.user, orden_id=orden_id
        )
        if (orden.estimacion_ref is not None
                and orden.estimacion_ref.eliminada
                and all(v.pk != orden.estimacion_ref_id for v in versiones)):
            versiones.append(orden.estimacion_ref)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.error(request, str(error))
        return redirect("costos_ordenes")

    initial = {
        "nombre_juego": orden.juego.nombre,
        "fecha_inicio": orden.fecha_inicio,
        "licencias_estimadas": orden.licencias_estimadas,
        "estimacion": orden.estimacion_ref_id or "",
    }
    form = OrdenEdicionForm(
        request.POST if request.method == "POST" else None,
        initial=initial, estimaciones=versiones,
    )
    if request.method == "POST" and form.is_valid():
        try:
            servicio.actualizar_orden(
                request.user, orden_id,
                nombre_juego=form.cleaned_data["nombre_juego"],
                fecha_inicio=form.cleaned_data["fecha_inicio"],
                estimacion_id=_int(form.cleaned_data["estimacion"]),
                licencias_estimadas=form.cleaned_data[
                    "licencias_estimadas"
                ],
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(request, "Orden de trabajo actualizada.")
            return redirect("costos_orden", orden_id=orden_id)
    return _render_orden(request, orden_id, form_orden=form)


@login_required
@require_http_methods(["GET", "POST"])
def orden_eliminar(request, orden_id):
    form = ConfirmarBajaForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        try:
            crear_orden_service().eliminar(request.user, orden_id)
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            messages.error(request, str(error))
            return redirect("costos_ordenes")
        messages.success(
            request, "Orden archivada. Sus costos y asientos se conservaron."
        )
        return redirect("costos_ordenes")
    return _render_orden(request, orden_id, form_baja=form)


@login_required
@require_POST
def orden_restaurar(request, orden_id):
    try:
        crear_orden_service().restaurar(request.user, orden_id)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Orden restaurada.")
    return redirect("costos_ordenes?estado=ELIMINADA")


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
        versiones = servicio.versiones_disponibles(
            request.user, orden_id=orden_id
        )
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


@login_required
@require_http_methods(["GET"])
def orden_evaluacion(request, orden_id):
    try:
        evaluacion = crear_orden_service().evaluar_rendimiento(
            request.user, orden_id
        )
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.warning(request, str(error))
        return redirect("costos_orden", orden_id=orden_id)
    return _render_orden(request, orden_id, evaluacion=evaluacion)


def _render_rendimiento(request, servicio, **extra):
    try:
        resultados = servicio.resultados_rendimiento(request.user)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    pagina = Paginator(resultados, REGISTROS_POR_PAGINA).get_page(
        request.GET.get("pagina")
    )
    grafico = [
        {
            "orden": f"OT-{fila['orden'].pk}",
            "juego": fila["orden"].juego.nombre,
            "estimacion": (
                f"{fila['orden'].estimacion_ref.juego.nombre} "
                f"v{fila['orden'].estimacion_ref.numero}"
            ),
            "estimado": str(fila["total_estimado"]),
            "real": str(fila["total_real"]),
        }
        for fila in pagina
        if (fila["total_estimado"] is not None
            and fila["total_real"] is not None)
    ]
    contexto = _contexto(request, screen="rendimiento")
    contexto.update(
        pagina=pagina,
        grafico_rendimiento=grafico,
        **extra,
    )
    return render(request, RENDIMIENTO_TEMPLATE, contexto)


@login_required
def consultar_rendimiento(request):
    return _render_rendimiento(request, crear_orden_service())


@login_required
@require_http_methods(["GET"])
def dashboard_api(request):
    """Entrega datos del dashboard sin habilitar acciones de costos."""
    try:
        resumen = crear_orden_service().resumen_dashboard(request.user)
    except SIN_PERMISO as error:
        return JsonResponse({"error": str(error)}, status=403)

    def fila_json(fila):
        orden = fila["orden"]
        evaluacion = fila["evaluacion"]
        return {
            "id": orden.pk,
            "juego": orden.juego.nombre,
            "estimacion": (
                f"{orden.estimacion_ref.juego.nombre} · v"
                f"{orden.estimacion_ref.numero}"
                if orden.estimacion_ref else None
            ),
            "totalEstimado": (
                str(fila["total_estimado"])
                if fila["total_estimado"] is not None else None
            ),
            "totalReal": (
                str(fila["total_real"])
                if fila["total_real"] is not None else None
            ),
            "variacion": (
                str(evaluacion["variacion"]) if evaluacion else None
            ),
            "porcentaje": (
                str(evaluacion["porcentaje"])
                if evaluacion and evaluacion["porcentaje"] is not None
                else None
            ),
            "viable": evaluacion["viable"] if evaluacion else None,
        }
    ultima_registrada = resumen["ultima_orden_registrada"]
    return JsonResponse({
        "ordenesPendientes": resumen["ordenes_pendientes"],
        "ordenesFinalizadas": resumen["ordenes_finalizadas"],
        "ultimaOrden": (
            fila_json(resumen["ultima_orden"])
            if resumen["ultima_orden"] else None
        ),
        "ultimaOrdenRegistrada": (
            {
                **fila_json(ultima_registrada),
                "estado": ultima_registrada["orden"].get_estado_display(),
                "fechaInicio": (
                    ultima_registrada["orden"].fecha_inicio.isoformat()
                ),
            }
            if ultima_registrada else None
        ),
        "ordenesFinalizadasRecientes": [
            fila_json(fila)
            for fila in resumen["ordenes_finalizadas_recientes"]
        ],
    })


@login_required
@require_http_methods(["GET"])
def evaluar_rentabilidad(request, orden_id):
    servicio = crear_orden_service()
    try:
        evaluacion = servicio.evaluar_rendimiento(request.user, orden_id)
        evaluacion["orden"] = servicio.detalle(request.user, orden_id)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.warning(request, str(error))
        return redirect("costos_rendimiento")
    return _render_rendimiento(
        request, servicio, modal_evaluacion=evaluacion
    )


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
        contrapartida_id=_int(datos.get("contrapartida")),
        clave=datos["clave"],
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
        fuentes_indirectas = servicio.fuentes_indirectas(request.user)
        cuentas_fuentes = servicio.cuentas_fuentes_disponibles(request.user)
        cuentas_excluidas = servicio.cuentas_indirectas_excluidas(request.user)
        cuentas_activas = servicio.cuentas(request.user)
        amortizacion = servicio.parametro_amortizacion(request.user)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    contexto = _contexto(request)
    contexto.update(
        amortizacion=amortizacion,
        amortizacion_modalidades=[("ANUAL", "Anual"), ("MENSUAL", "Mensual"),
                                  ("DIARIA", "Diaria")],
        procesos=procesos,
        fuentes_indirectas=fuentes_indirectas,
        cuentas_fuentes=cuentas_fuentes,
        cuentas_excluidas=cuentas_excluidas,
        cuentas_activas=cuentas_activas,
        elementos=[(e.value, e.label, configuraciones.get(e.value))
                   for e in Elemento],
        **extra,
    )
    return render(request, CATALOGOS_TEMPLATE, contexto)


@login_required
def catalogos(request):
    return _render_catalogos(request)


@login_required
@require_POST
def amortizacion_editar(request):
    form = AmortizacionForm(request.POST)
    if form.is_valid():
        try:
            crear_catalogo_costos_service().guardar_parametro_amortizacion(
                request.user, **form.cleaned_data
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Amortización de videojuegos "
                                      "actualizada.")
    else:
        messages.error(request, "Revisa la modalidad y la vida útil.")
    return redirect("costos_catalogos")


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


@login_required
@require_http_methods(["GET", "POST"])
def fuente_indirecta_nueva(request):
    servicio = crear_catalogo_costos_service()
    try:
        cuentas = servicio.cuentas_fuentes_disponibles(request.user)
        procesos = servicio.procesos(request.user)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    form = FuenteIndirectaForm(
        request.POST if request.method == "POST" else None,
        cuentas=cuentas, procesos=procesos,
    )
    if request.method == "POST" and form.is_valid():
        cuenta, proceso = form.objetos_elegidos()
        try:
            servicio.crear_fuente_indirecta(
                request.user,
                nombre=form.cleaned_data["nombre"],
                tipo=form.cleaned_data["tipo"],
                cuenta=cuenta, proceso=proceso,
                exclusiva_desarrollo=form.cleaned_data[
                    "exclusiva_desarrollo"
                ],
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(
                request, "Fuente indirecta exclusiva de desarrollo guardada."
            )
            return redirect("costos_catalogos")
    return _render_catalogos(request, form_fuente=form)


@login_required
@require_http_methods(["GET", "POST"])
def cuenta_indirecta_excluir(request):
    servicio = crear_catalogo_costos_service()
    try:
        cuentas = servicio.cuentas(request.user)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    form = ExcluirCuentaIndirectaForm(
        request.POST if request.method == "POST" else None,
        cuentas=cuentas,
    )
    if request.method == "POST" and form.is_valid():
        try:
            servicio.excluir_cuenta_indirecta(
                request.user, cuenta=form.cuenta_elegida(),
                motivo=form.cleaned_data["motivo"],
            )
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            _error_en_form(form, error)
        else:
            messages.success(request, "Cuenta excluida de los indirectos.")
            return redirect("costos_catalogos")
    return _render_catalogos(request, form_excluir=form)


@login_required
@require_POST
def cuenta_indirecta_habilitar(request, exclusion_id):
    servicio = crear_catalogo_costos_service()
    form = ConfirmarCambioForm(request.POST)
    if form.is_valid():
        try:
            servicio.quitar_exclusion_indirecta(request.user, exclusion_id)
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Cuenta retirada de exclusiones.")
    else:
        messages.error(request, "Confirma el cambio para habilitar la cuenta.")
    return redirect("costos_catalogos")


def _render_indirectos(request, *, periodo_id=None, preview=None,
                       form_periodo=None, form_aplicar=None,
                       form_revertir=None):
    servicio = crear_aplicacion_indirectos_service()
    try:
        periodos = servicio.periodos(request.user)
    except SIN_PERMISO as error:
        _sin_permiso(error)
    if form_periodo is None:
        form_periodo = PeriodoIndirectoForm(
            initial={"periodo": str(periodo_id or "")}, periodos=periodos
        )
    if periodo_id and preview is None:
        try:
            preview = servicio.previsualizar(request.user, periodo_id)
        except SIN_PERMISO as error:
            _sin_permiso(error)
        except CostosError as error:
            messages.error(request, str(error))
    if preview is not None:
        accion = request.GET.get("accion")
        inicial = {"periodo": str(preview["periodo"].pk)}
        if (accion == "aplicar" and preview["puede_aplicar"]
                and preview["periodo_abierto"]):
            form_aplicar = AplicarIndirectosForm(
                initial=inicial, periodos=periodos
            )
        elif (accion == "revertir" and preview["puede_revertir"]
              and preview["periodo_abierto"]):
            form_revertir = RevertirIndirectosForm(
                initial=inicial, periodos=periodos
            )
    contexto = _contexto(request)
    contexto.update(
        periodos=periodos, form_periodo=form_periodo, preview=preview,
        form_aplicar=form_aplicar, form_revertir=form_revertir,
    )
    return render(request, INDIRECTOS_TEMPLATE, contexto)


@login_required
@require_http_methods(["GET", "POST"])
def indirectos_periodo(request):
    if request.method == "POST":
        servicio = crear_aplicacion_indirectos_service()
        try:
            periodos = servicio.periodos(request.user)
        except SIN_PERMISO as error:
            _sin_permiso(error)
        form = PeriodoIndirectoForm(request.POST, periodos=periodos)
        if form.is_valid():
            return redirect(
                f"{reverse('costos_indirectos_periodo')}?periodo="
                f"{form.cleaned_data['periodo'].pk}"
            )
        return _render_indirectos(request, form_periodo=form)
    periodo_id = request.GET.get("periodo")
    return _render_indirectos(request, periodo_id=periodo_id)


@login_required
@require_POST
def indirectos_aplicar(request):
    try:
        periodos = crear_aplicacion_indirectos_service().periodos(
            request.user
        )
    except SIN_PERMISO as error:
        _sin_permiso(error)
    form = AplicarIndirectosForm(request.POST, periodos=periodos)
    if not form.is_valid():
        messages.error(request, "Confirma el período y la distribución.")
        return redirect("costos_indirectos_periodo")
    periodo = form.cleaned_data["periodo"]
    try:
        resultado = crear_aplicacion_indirectos_service().aplicar(
            request.user, periodo.pk
        )
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.error(request, str(error))
    else:
        if resultado["estado"] == "APLICADA":
            messages.success(request, "Indirectos del período aplicados.")
        elif resultado["alertas"]:
            messages.warning(request, "No se aplicaron importes: revisa las "
                                      "alertas del período.")
    return redirect(
        f"{reverse('costos_indirectos_periodo')}?periodo={periodo.pk}"
    )


@login_required
@require_POST
def indirectos_revertir(request):
    try:
        periodos = crear_aplicacion_indirectos_service().periodos(
            request.user
        )
    except SIN_PERMISO as error:
        _sin_permiso(error)
    form = RevertirIndirectosForm(request.POST, periodos=periodos)
    if not form.is_valid():
        messages.error(request, "Confirma la reversión del período.")
        return redirect("costos_indirectos_periodo")
    periodo = form.cleaned_data["periodo"]
    try:
        resultado = crear_aplicacion_indirectos_service().revertir(
            request.user, periodo.pk
        )
    except SIN_PERMISO as error:
        _sin_permiso(error)
    except CostosError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Aplicación de indirectos revertida.")
    return redirect(
        f"{reverse('costos_indirectos_periodo')}?periodo={periodo.pk}"
    )
