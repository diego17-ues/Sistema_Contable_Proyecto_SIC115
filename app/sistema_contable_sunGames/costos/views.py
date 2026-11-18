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
    crear_calculo_service,
    crear_catalogo_costos_service,
    crear_orden_service,
)
from .exceptions import CostosError
from .forms import (
    CargoForm,
    ConfirmForm,
    CostoProcesoForm,
    CorteForm,
    DepreciacionForm,
    EquipoForm,
    FiltroOrdenForm,
    FondoForm,
    HoraForm,
    MapeoForm,
    OrdenForm,
    ParametroForm,
    ProcesoForm,
    SalarioForm,
    TasasForm,
    UsoEquipoForm,
)
from .models import CONCEPTOS_CUENTA, TIPOS_USO_EQUIPO, CargoOrden

ORDENES_TEMPLATE = "costos/ordenes.html"
ORDEN_TEMPLATE = "costos/orden.html"
CATALOGOS_TEMPLATE = "costos/catalogos.html"
REGISTROS_POR_PAGINA = 50
SIN_PERMISO = (RolNoAutorizadoError, UsuarioInactivoError)
VISTAS_ORDEN = ("cargos", "horas", "cortes")


def _manejar_error(request, error):
    if isinstance(error, SIN_PERMISO):
        raise PermissionDenied(str(error)) from error
    messages.error(request, str(error))


def _contexto(request, screen="costos"):
    return contexto_panel(request, screen)


def _roles_disponibles(servicio_catalogo, actor):
    return sorted({s.rol for s in servicio_catalogo.salarios(actor)})


# ---------------------------------------------------------------- listas

@login_required
def ordenes(request):
    servicio = crear_orden_service()
    filtro = FiltroOrdenForm(request.GET or None)
    estado = filtro["estado"].value() if filtro.is_valid() else None
    try:
        lista = servicio.listar(
            request.user, estado=estado or None
        )
    except SIN_PERMISO as error:
        raise PermissionDenied(str(error)) from error
    pagina = Paginator(lista, REGISTROS_POR_PAGINA).get_page(
        request.GET.get("pagina")
    )
    contexto = _contexto(request)
    contexto.update(
        filtro=filtro, pagina=pagina, estado=estado or "",
    )
    return render(request, ORDENES_TEMPLATE, contexto)


@login_required
def orden_nueva(request):
    servicio = crear_orden_service()
    if request.method == "POST":
        form = OrdenForm(request.POST)
        if form.is_valid():
            try:
                orden = servicio.crear_orden(
                    request.user,
                    nombre_juego=form.cleaned_data["nombre_juego"],
                    capitalizable_desde=form.cleaned_data[
                        "capitalizable_desde"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                _manejar_error(request, error)
                messages.error(request, str(error))
            else:
                messages.success(request, "Orden de trabajo creada.")
                return redirect("costos_orden", orden_id=orden.pk)
    else:
        form = OrdenForm()
    # Re-render lista con el modal abierto y errores.
    filtro = FiltroOrdenForm()
    lista = servicio.listar(request.user)
    contexto = _contexto(request)
    contexto.update(
        filtro=filtro,
        pagina=Paginator(lista, REGISTROS_POR_PAGINA).get_page(1),
        estado="", form_nueva=form,
    )
    return render(request, ORDENES_TEMPLATE, contexto)


@login_required
def orden_detalle(request, orden_id):
    servicio = crear_orden_service()
    catalogo = crear_catalogo_costos_service()
    calculo = crear_calculo_service()
    vista = request.GET.get("vista", "cargos")
    if vista not in VISTAS_ORDEN:
        vista = "cargos"
    try:
        orden = servicio.detalle(request.user, orden_id)
        horas = orden.horas.all()[:200]
        cargos = orden.cargos.all()[:300]
        cortes = [c for c in catalogo.cortes(request.user)
                  if any(d.orden_id == orden.pk for d in c.detalles.all())]
        roles = _roles_disponibles(catalogo, request.user)
        procesos = catalogo.procesos(request.user)
    except (CostosError, *SIN_PERMISO) as error:
        _manejar_error(request, error)
        return redirect("costos_ordenes")
    contexto = _contexto(request)
    contexto.update(
        orden=orden, vista=vista, horas=horas, cargos=cargos,
        cortes=cortes, roles=roles, procesos=procesos,
        saldos=servicio.saldos_orden(orden),
        conceptos_cuenta=CONCEPTOS_CUENTA,
        origenes=CargoOrden.ORIGENES,
    )
    return render(request, ORDEN_TEMPLATE, contexto)


@login_required
@require_http_methods(["GET", "POST"])
def hora_nueva(request, orden_id):
    servicio = crear_orden_service()
    catalogo = crear_catalogo_costos_service()
    if request.method == "POST":
        form = HoraForm(
            request.POST,
            procesos=catalogo.procesos(request.user),
            roles=_roles_disponibles(catalogo, request.user),
        )
        if form.is_valid():
            datos = form.cleaned_data
            try:
                servicio.registrar_hora(
                    request.user, orden_id,
                    proceso_id=int(datos["proceso"]) if datos["proceso"] else None,
                    rol=datos["rol"], horas=datos["horas"],
                    fecha=datos["fecha"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Horas registradas.")
                return redirect("costos_orden", orden_id=orden_id)
    else:
        form = HoraForm(
            procesos=catalogo.procesos(request.user),
            roles=_roles_disponibles(catalogo, request.user),
        )
    return _render_orden_modal(request, orden_id, form_hora=form)


@login_required
@require_http_methods(["GET", "POST"])
def cargo_nuevo(request, orden_id):
    servicio = crear_orden_service()
    if request.method == "POST":
        form = CargoForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                servicio.registrar_cargo(
                    request.user, orden_id,
                    origen=datos["origen"],
                    afecta_mayor=datos["afecta_mayor"],
                    monto=datos["monto"], fecha=datos["fecha"],
                    descripcion=datos["descripcion"],
                    concepto_cuenta=datos["concepto_cuenta"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Cargo registrado.")
                return redirect("costos_orden", orden_id=orden_id)
    else:
        form = CargoForm()
    return _render_orden_modal(request, orden_id, form_cargo=form)


@login_required
@require_http_methods(["GET", "POST"])
def orden_cerrar(request, orden_id):
    servicio = crear_orden_service()
    if request.method == "POST":
        form = ConfirmForm(request.POST)
        if form.is_valid():
            try:
                servicio.cerrar_orden(
                    request.user, orden_id,
                    confirmacion=form.cleaned_data["confirmacion"],
                    motivo=form.cleaned_data["motivo"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Orden cerrada.")
                return redirect("costos_orden", orden_id=orden_id)
    else:
        form = ConfirmForm()
    return _render_orden_modal(request, orden_id, form_cierre=form)


def _render_orden_modal(request, orden_id, **forms_ctx):
    servicio = crear_orden_service()
    catalogo = crear_catalogo_costos_service()
    vista = request.GET.get("vista", "cargos")
    if vista not in VISTAS_ORDEN:
        vista = "cargos"
    try:
        orden = servicio.detalle(request.user, orden_id)
        horas = orden.horas.all()[:200]
        cargos = orden.cargos.all()[:300]
        cortes = catalogo.cortes(request.user)
        roles = _roles_disponibles(catalogo, request.user)
        procesos = catalogo.procesos(request.user)
    except (CostosError, *SIN_PERMISO) as error:
        _manejar_error(request, error)
        return redirect("costos_ordenes")
    contexto = _contexto(request)
    defaults = dict(
        orden=orden, vista=vista, horas=horas, cargos=cargos,
        cortes=cortes, roles=roles, procesos=procesos,
        saldos=servicio.saldos_orden(orden),
        conceptos_cuenta=CONCEPTOS_CUENTA,
        origenes=CargoOrden.ORIGENES,
    )
    defaults.update(forms_ctx)
    contexto.update(defaults)
    return render(request, ORDEN_TEMPLATE, contexto)


# ------------------------------------------------------------- catálogos

@login_required
def catalogos(request):
    return _render_catalogos(request)


def _render_catalogos(request, **extra):
    catalogo = crear_catalogo_costos_service()
    calculo = crear_calculo_service()
    try:
        procesos = catalogo.procesos(request.user)
        parametros = catalogo.parametros(request.user)
        salarios = catalogo.salarios(request.user)
        mapeos = catalogo.mapeos(request.user)
        fondos = catalogo.fondos(request.user)
        equipos = catalogo.equipos(request.user)
        cortes = catalogo.cortes(request.user)
        periodos = catalogo.periodos(request.user)
        costos_proceso, periodo_cp = calculo.costos_proceso(request.user)
        cuentas = catalogo.cuentas_posteables(request.user)
    except SIN_PERMISO as error:
        raise PermissionDenied(str(error)) from error
    contexto = _contexto(request)
    contexto.update(
        procesos=procesos, parametros=parametros, salarios=salarios,
        mapeos=mapeos, fondos=fondos, equipos=equipos, cortes=cortes,
        periodos=periodos, costos_proceso=costos_proceso,
        periodo_cp=periodo_cp,
        conceptos_cuenta=CONCEPTOS_CUENTA,
        tipos_uso=TIPOS_USO_EQUIPO,
        form_tasas=TasasForm(periodos=periodos),
        form_depreciacion=DepreciacionForm(),
        **extra,
    )
    return render(request, CATALOGOS_TEMPLATE, contexto)


@login_required
@require_http_methods(["GET", "POST"])
def proceso_nuevo(request):
    catalogo = crear_catalogo_costos_service()
    if request.method == "POST":
        form = ProcesoForm(request.POST)
        if form.is_valid():
            try:
                catalogo.crear_proceso(
                    request.user, nombre=form.cleaned_data["nombre"],
                    descripcion=form.cleaned_data["descripcion"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Proceso registrado.")
                return redirect("costos_catalogos")
    else:
        form = ProcesoForm()
    return _render_catalogos(request, form_proceso=form)


@login_required
@require_http_methods(["GET", "POST"])
def costo_proceso_nuevo(request):
    calculo = crear_calculo_service()
    catalogo = crear_catalogo_costos_service()
    procesos = catalogo.procesos(request.user)
    periodos = catalogo.periodos(request.user)
    if request.method == "POST":
        form = CostoProcesoForm(request.POST, procesos=procesos,
                                periodos=periodos)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                calculo.registrar_costo_proceso(
                    request.user,
                    proceso_id=int(datos["proceso"]),
                    periodo_id=int(datos["periodo"]),
                    costo=datos["costo"], horas_base=datos["horas_base"],
                    tasa_presupuestada=datos["tasa_presupuestada"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Costo de proceso registrado.")
                return redirect("costos_catalogos")
    else:
        form = CostoProcesoForm(procesos=procesos, periodos=periodos)
    return _render_catalogos(request, form_costo_proceso=form)


@login_required
@require_http_methods(["GET", "POST"])
def parametro_nuevo(request):
    catalogo = crear_catalogo_costos_service()
    if request.method == "POST":
        form = ParametroForm(request.POST)
        if form.is_valid():
            try:
                catalogo.crear_parametro(
                    request.user, **form.cleaned_data
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Parámetro registrado.")
                return redirect("costos_catalogos")
    else:
        form = ParametroForm()
    return _render_catalogos(request, form_parametro=form)


@login_required
@require_http_methods(["GET", "POST"])
def salario_nuevo(request):
    catalogo = crear_catalogo_costos_service()
    if request.method == "POST":
        form = SalarioForm(request.POST)
        if form.is_valid():
            try:
                catalogo.crear_salario(
                    request.user, **form.cleaned_data
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Salario de referencia registrado.")
                return redirect("costos_catalogos")
    else:
        form = SalarioForm()
    return _render_catalogos(request, form_salario=form)


@login_required
@require_http_methods(["GET", "POST"])
def mapeo_nuevo(request):
    catalogo = crear_catalogo_costos_service()
    cuentas = catalogo.cuentas_posteables(request.user)
    if request.method == "POST":
        form = MapeoForm(request.POST, cuentas=cuentas)
        if form.is_valid():
            try:
                catalogo.crear_mapeo(
                    request.user, concepto=form.cleaned_data["concepto"],
                    cuenta_codigo=form.cleaned_data["cuenta"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Mapeo de cuenta registrado.")
                return redirect("costos_catalogos")
    else:
        form = MapeoForm(cuentas=cuentas)
    return _render_catalogos(request, form_mapeo=form)


@login_required
@require_http_methods(["GET", "POST"])
def fondo_nuevo(request):
    calculo = crear_calculo_service()
    if request.method == "POST":
        form = FondoForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                calculo.crear_fondo(
                    request.user, nombre=datos["nombre"], monto=datos["monto"],
                    fecha=datos["fecha"], descripcion=datos["descripcion"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Fondo compartido registrado.")
                return redirect("costos_catalogos")
    else:
        form = FondoForm()
    return _render_catalogos(request, form_fondo=form)


@login_required
@require_POST
def fondo_distribuir(request, fondo_id):
    calculo = crear_calculo_service()
    try:
        calculo.distribuir_fondo(request.user, fondo_id)
    except (CostosError, *SIN_PERMISO) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Fondo distribuido entre las órdenes.")
    return redirect("costos_catalogos")


@login_required
@require_http_methods(["GET", "POST"])
def equipo_nuevo(request):
    catalogo = crear_catalogo_costos_service()
    ordenes = catalogo.ordenes_abiertas(request.user)
    if request.method == "POST":
        form = EquipoForm(request.POST, ordenes=ordenes)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                catalogo.crear_equipo(
                    request.user,
                    nombre=datos["nombre"], costo=datos["costo"],
                    valor_residual=datos["valor_residual"] or 0,
                    vida_util_meses=datos["vida_util_meses"],
                    tipo_uso=datos["tipo_uso"],
                    orden_id=int(datos["orden"]) if datos["orden"] else None,
                    horas_mes=datos["horas_mes"] or 0,
                    fecha_adquisicion=datos["fecha_adquisicion"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Equipo registrado.")
                return redirect("costos_catalogos")
    else:
        form = EquipoForm(ordenes=ordenes)
    return _render_catalogos(request, form_equipo=form)


@login_required
@require_http_methods(["GET", "POST"])
def uso_equipo_nuevo(request, equipo_id):
    catalogo = crear_catalogo_costos_service()
    ordenes = list(catalogo.ordenes_abiertas(request.user))
    if request.method == "POST":
        form = UsoEquipoForm(request.POST, ordenes=ordenes)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                catalogo.crear_uso_equipo(
                    request.user,
                    equipo_id=equipo_id, orden_id=int(datos["orden"]),
                    fecha=datos["fecha"], horas=datos["horas"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Uso de equipo registrado.")
                return redirect("costos_catalogos")
    else:
        form = UsoEquipoForm(initial={"equipo": equipo_id},
                             ordenes=ordenes)
    return _render_catalogos(
        request, form_uso=form, uso_equipo_id=equipo_id,
        uso_ordenes=ordenes,
    )


@login_required
@require_POST
def tasas_aplicar(request):
    calculo = crear_calculo_service()
    form = TasasForm(request.POST, periodos=crear_catalogo_costos_service()
                     .periodos(request.user))
    if form.is_valid():
        try:
            resultados = calculo.aplicar_tasas(
                request.user, int(form.cleaned_data["periodo"]),
                usar_presupuestada=form.cleaned_data["usar_presupuestada"],
            )
        except (CostosError, *SIN_PERMISO) as error:
            messages.error(request, str(error))
        else:
            for r in resultados:
                messages.success(
                    request,
                    f"{r['proceso']}: tasa {r['tasa']} ({r['origen_tasa']}), "
                    f"aplicado ${r['aplicado']}, ajuste ${r['diferencia']}",
                )
    else:
        messages.error(request, "Revise el período seleccionado.")
    return redirect("costos_catalogos")


@login_required
@require_POST
def depreciacion_generar(request):
    calculo = crear_calculo_service()
    form = DepreciacionForm(request.POST)
    if form.is_valid():
        try:
            generados = calculo.generar_depreciacion(
                request.user, anio=form.cleaned_data["anio"],
                mes=form.cleaned_data["mes"],
            )
        except (CostosError, *SIN_PERMISO) as error:
            messages.error(request, str(error))
        else:
            if generados:
                messages.success(
                    request, f"{len(generados)} cargo(s) de depreciación: "
                    + "; ".join(generados[:5])
                )
            else:
                messages.info(request,
                              "No se generaron cargos (equipo ocioso o "
                              "sin uso registrado).")
    else:
        messages.error(request, "Revise el año y el mes.")
    return redirect("costos_catalogos")


@login_required
@require_http_methods(["GET", "POST"])
def corte_nuevo(request):
    calculo = crear_calculo_service()
    catalogo = crear_catalogo_costos_service()
    periodos = catalogo.periodos(request.user)
    if request.method == "POST":
        form = CorteForm(request.POST, periodos=periodos)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                calculo.crear_corte(
                    request.user, periodo_id=int(datos["periodo"]),
                    tipo=datos["tipo"], motivo=datos["motivo"],
                )
            except (CostosError, *SIN_PERMISO) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Corte de costos registrado.")
                return redirect("costos_catalogos")
    else:
        form = CorteForm(periodos=periodos)
    return _render_catalogos(request, form_corte=form)


@login_required
@require_POST
def corte_revertir(request, corte_id):
    calculo = crear_calculo_service()
    try:
        calculo.revertir_corte(request.user, corte_id)
    except (CostosError, *SIN_PERMISO) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Corte provisional revertido.")
    return redirect("costos_catalogos")
