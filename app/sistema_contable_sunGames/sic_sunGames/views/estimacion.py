"""Pantallas del módulo de estimación (subsistema de costos)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from estimacion.composition import (
    crear_estimacion_service,
    crear_presupuesto_service,
)
from estimacion.exceptions import EstimacionError, VersionInmutableError
from estimacion.forms import (
    CostoForm,
    CostoIndirectoForm,
    EstimacionForm,
    ExpertoForm,
    JuegoForm,
    ParametroForm,
    RolForm,
    SalarioForm,
)
from usuarios.exceptions import UsuarioError

from .pages import contexto_panel

JUEGOS_TEMPLATE = "sic_sunGames/estimacion.html"
JUEGO_TEMPLATE = "sic_sunGames/estimacion_juego.html"
CATALOGOS_TEMPLATE = "sic_sunGames/estimacion_catalogos.html"
REGISTROS_POR_PAGINA = 20


def _sin_permiso(error):
    return PermissionDenied(str(error))


def _pagina(request, registros):
    return Paginator(registros, REGISTROS_POR_PAGINA).get_page(
        request.GET.get("pagina")
    )


def _render_juegos(request, servicio, **extra):
    try:
        juegos = servicio.listar_juegos(request.user)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    contexto = contexto_panel(request, "estimacion")
    contexto.update(pagina=_pagina(request, juegos), **extra)
    return render(request, JUEGOS_TEMPLATE, contexto)


def _contexto_juego(request, juego_id, servicio, **extra):
    try:
        juego = servicio.obtener_juego(request.user, juego_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    contexto = contexto_panel(request, "estimacion")
    catalogos = servicio.catalogos(request.user)
    fases = list(juego.fases.all())
    estimaciones = servicio.estimaciones(request.user, juego_id)
    ronda_actual = _ronda_actual(request, juego, fases)
    consolidacion = _consolidacion(request, servicio, juego, ronda_actual)
    versiones = list(crear_presupuesto_service().versiones(
        request.user, juego_id
    ))
    presupuesto_service = crear_presupuesto_service()
    for version in versiones:
        version.total_estimado = presupuesto_service.total(version)
    contexto.update(
        juego=juego,
        fases=fases,
        roles=catalogos["roles"],
        expertos=catalogos["expertos"],
        estimaciones=estimaciones,
        rondas=list(juego.rondas.all()),
        ronda_actual=ronda_actual,
        consolidacion=consolidacion,
        versiones=versiones,
        **extra,
    )
    return contexto


def _ronda_actual(request, juego, fases):
    """Ronda seleccionada; por defecto la última con estimaciones."""
    numeros = sorted({
        e.ronda for e in juego.estimaciones.all()
    } | {r.numero for r in juego.rondas.all()})
    if not numeros:
        return None
    try:
        pedida = int(request.GET.get("ronda", ""))
    except ValueError:
        pedida = 0
    return pedida if pedida in numeros else numeros[-1]


def _consolidacion(request, servicio, juego, ronda):
    if ronda is None:
        return []
    try:
        return servicio.consolidar(request.user, juego.pk, ronda)
    except UsuarioError as error:
        raise _sin_permiso(error) from error


@login_required
def estimaciones(request):
    return _render_juegos(request, crear_estimacion_service())


@login_required
@require_http_methods(["GET", "POST"])
def juego_nuevo(request):
    servicio = crear_estimacion_service()
    if request.method != "POST":
        return _render_juegos(request, servicio, form=JuegoForm())
    form = JuegoForm(request.POST)
    if form.is_valid():
        fases = [(nombre, orden) for orden, nombre in
                 enumerate(form.cleaned_data["fases"], start=1)]
        try:
            servicio.crear_juego(
                request.user, form.cleaned_data["nombre"], fases
            )
        except UsuarioError as error:
            raise _sin_permiso(error) from error
        except EstimacionError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, "Juego registrado.")
            return redirect("estimacion")
    return _render_juegos(request, servicio, form=form)


@login_required
def juego_detalle(request, juego_id):
    servicio = crear_estimacion_service()
    return render(
        request, JUEGO_TEMPLATE,
        _contexto_juego(request, juego_id, servicio),
    )


@login_required
@require_http_methods(["GET", "POST"])
def estimacion_nueva(request, juego_id):
    servicio = crear_estimacion_service()
    if request.method != "POST":
        return render(
            request, JUEGO_TEMPLATE,
            _contexto_juego(
                request, juego_id, servicio, form=EstimacionForm()
            ),
        )
    form = EstimacionForm(request.POST)
    if form.is_valid():
        datos = form.cleaned_data
        try:
            servicio.registrar_estimacion(
                request.user,
                juego_id=juego_id,
                fase_id=datos["fase"],
                rol_id=datos["rol"],
                experto_id=datos["experto"],
                ronda=datos["ronda"],
                optimista=datos["optimista"],
                moda=datos["moda"],
                pesimista=datos["pesimista"],
                justificacion=datos["justificacion"],
            )
        except UsuarioError as error:
            raise _sin_permiso(error) from error
        except EstimacionError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, "Estimación registrada.")
            return redirect("estimacion_juego", juego_id=juego_id)
    return render(
        request, JUEGO_TEMPLATE,
        _contexto_juego(request, juego_id, servicio, form=form),
    )


@login_required
@require_http_methods(["GET", "POST"])
def ronda_cerrar(request, juego_id, numero):
    servicio = crear_estimacion_service()
    if request.method == "POST":
        try:
            servicio.cerrar_ronda(request.user, juego_id, numero)
        except UsuarioError as error:
            raise _sin_permiso(error) from error
        except EstimacionError as error:
            messages.error(request, str(error))
        else:
            messages.success(
                request, f"Ronda {numero} cerrada y aprobada."
            )
        return redirect("estimacion_juego", juego_id=juego_id)
    return render(
        request, JUEGO_TEMPLATE,
        _contexto_juego(
            request, juego_id, servicio,
            resumen_ronda={"numero": numero},
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def version_generar(request, juego_id):
    servicio = crear_presupuesto_service()
    if request.method != "POST":
        return render(
            request, JUEGO_TEMPLATE,
            _contexto_juego(request, juego_id, crear_estimacion_service(),
                            form_version=True),
        )
    try:
        version = servicio.generar_version(request.user, juego_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request, f"Versión {version.numero} generada en borrador."
        )
    return redirect("estimacion_juego", juego_id=juego_id)


@login_required
@require_http_methods(["GET", "POST"])
def version_costo_directo(request, version_id):
    return _version_costo(
        request, version_id, crear_presupuesto_service(),
        CostoForm, directo=True,
    )


@login_required
@require_http_methods(["GET", "POST"])
def version_costo_indirecto(request, version_id):
    return _version_costo(
        request, version_id, crear_presupuesto_service(),
        CostoIndirectoForm, directo=False,
    )


def _version_costo(request, version_id, servicio, clase_form, *, directo):
    try:
        version = servicio.obtener_version(request.user, version_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    juego_id = version.juego_id
    if request.method == "POST":
        form = clase_form(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                if directo:
                    servicio.agregar_costo_directo(
                        request.user, version_id,
                        datos["concepto"], datos["monto"],
                    )
                else:
                    servicio.agregar_costo_indirecto(
                        request.user, version_id,
                        datos["concepto"], datos["monto"],
                    )
            except UsuarioError as error:
                raise _sin_permiso(error) from error
            except EstimacionError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Costo registrado.")
                return redirect("estimacion_juego", juego_id=juego_id)
        ruta = (
            "estimacion_costo_directo" if directo
            else "estimacion_costo_indirecto"
        )
        return render(
            request, JUEGO_TEMPLATE,
            _contexto_juego(
                request, juego_id, crear_estimacion_service(),
                form_costo=form, costo_directo=directo,
                costo_url=reverse(ruta, args=[version_id]),
            ),
        )
    ruta = (
        "estimacion_costo_directo" if directo
        else "estimacion_costo_indirecto"
    )
    return render(
        request, JUEGO_TEMPLATE,
        _contexto_juego(
            request, juego_id, crear_estimacion_service(),
            form_costo=clase_form(), costo_directo=directo,
            costo_url=reverse(ruta, args=[version_id]),
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def version_aprobar(request, version_id):
    servicio = crear_presupuesto_service()
    try:
        version = servicio.obtener_version(request.user, version_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    if request.method != "POST":
        return render(
            request, JUEGO_TEMPLATE,
            _contexto_juego(
                request, version.juego_id, crear_estimacion_service(),
                resumen_version=version, accion="aprobar",
            ),
        )
    try:
        servicio.aprobar(request.user, version_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request, f"Versión {version.numero} aprobada."
        )
    return redirect("estimacion_juego", juego_id=version.juego_id)


@login_required
@require_http_methods(["GET", "POST"])
def version_vigente(request, version_id):
    servicio = crear_presupuesto_service()
    try:
        version = servicio.obtener_version(request.user, version_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    if request.method != "POST":
        return render(
            request, JUEGO_TEMPLATE,
            _contexto_juego(
                request, version.juego_id, crear_estimacion_service(),
                resumen_version=version, accion="vigente",
            ),
        )
    try:
        servicio.marcar_vigente(
            request.user, version.juego_id, version_id
        )
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request, f"Versión {version.numero} marcada como vigente."
        )
    return redirect("estimacion_juego", juego_id=version.juego_id)


@login_required
def estimacion_catalogos(request):
    servicio = crear_estimacion_service()
    try:
        parametros = servicio.parametros(request.user)
        salarios = servicio.salarios(request.user)
        catalogos = servicio.catalogos(request.user)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    contexto = contexto_panel(request, "estimacion")
    contexto.update(
        pagina=_pagina(request, parametros),
        parametros=parametros,
        salarios=salarios,
        roles=catalogos["roles"],
        expertos=catalogos["expertos"],
        form_rol=None, form_experto=None, form_parametro=None,
        form_salario=None,
    )
    return render(request, CATALOGOS_TEMPLATE, contexto)


@login_required
@require_http_methods(["GET", "POST"])
def catalogo_rol(request):
    return _catalogo_form(request, RolForm, "rol")


@login_required
@require_http_methods(["GET", "POST"])
def catalogo_experto(request):
    return _catalogo_form(request, ExpertoForm, "experto")


def _catalogo_form(request, clase_form, tipo):
    servicio = crear_estimacion_service()
    if request.method == "POST":
        form = clase_form(request.POST)
        if form.is_valid():
            try:
                if tipo == "rol":
                    servicio.crear_rol(
                        request.user,
                        form.cleaned_data["nombre"],
                        form.cleaned_data["nivel"],
                    )
                else:
                    servicio.crear_experto(
                        request.user, form.cleaned_data["nombre"]
                    )
            except UsuarioError as error:
                raise _sin_permiso(error) from error
            except EstimacionError as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, "Registro agregado.")
                return redirect("estimacion_catalogos")
        return _render_catalogo(request, servicio, form=form, tipo=tipo)
    return _render_catalogo(
        request, servicio, form=clase_form(), tipo=tipo
    )


def _render_catalogo(request, servicio, *, form=None, tipo=None):
    try:
        parametros = servicio.parametros(request.user)
        salarios = servicio.salarios(request.user)
        catalogos = servicio.catalogos(request.user)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    contexto = contexto_panel(request, "estimacion")
    extras = {
        "parametros": parametros,
        "salarios": salarios,
        "roles": catalogos["roles"],
        "expertos": catalogos["expertos"],
        "pagina": _pagina(request, parametros),
    }
    clave = {
        "rol": "form_rol", "experto": "form_experto",
        "parametro": "form_parametro", "salario": "form_salario",
    }.get(tipo)
    if clave:
        extras[clave] = form
    return render(request, CATALOGOS_TEMPLATE, {**contexto, **extras})


@login_required
@require_http_methods(["GET", "POST"])
def catalogo_parametro(request):
    servicio = crear_estimacion_service()
    if request.method == "POST":
        form = ParametroForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                servicio.crear_parametro(
                    request.user,
                    clave=datos["clave"],
                    valor=datos["valor"],
                    vigente_desde=datos["vigente_desde"],
                    vigente_hasta=datos["vigente_hasta"] or None,
                    verificado=datos["verificado"],
                )
            except UsuarioError as error:
                raise _sin_permiso(error) from error
            except EstimacionError as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, "Parámetro registrado.")
                return redirect("estimacion_catalogos")
        return _render_catalogo(
            request, servicio, form=form, tipo="parametro"
        )
    return _render_catalogo(
        request, servicio, form=ParametroForm(), tipo="parametro"
    )


@login_required
@require_http_methods(["GET", "POST"])
def catalogo_salario(request):
    servicio = crear_estimacion_service()
    if request.method == "POST":
        form = SalarioForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                servicio.crear_salario(
                    request.user,
                    rol_id=datos["rol"],
                    salario_bruto=datos["salario_bruto"],
                    vigente_desde=datos["vigente_desde"],
                    vigente_hasta=datos["vigente_hasta"] or None,
                )
            except UsuarioError as error:
                raise _sin_permiso(error) from error
            except EstimacionError as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, "Salario de referencia registrado.")
                return redirect("estimacion_catalogos")
        return _render_catalogo(
            request, servicio, form=form, tipo="salario"
        )
    return _render_catalogo(
        request, servicio, form=SalarioForm(), tipo="salario"
    )
