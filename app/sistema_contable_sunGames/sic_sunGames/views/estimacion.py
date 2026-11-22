"""Pantallas del módulo de estimación (subsistema de costos)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from estimacion.composition import (
    crear_estimacion_service,
    crear_presupuesto_service,
)
from estimacion.exceptions import EstimacionError, VersionInmutableError
from estimacion.forms import (
    ConfirmarBajaForm,
    CostoForm,
    CostoIndirectoForm,
    EstimacionExpertoEdicionForm,
    EstimacionMatrizForm,
    ExpertoForm,
    JuegoForm,
    ParametroEdicionForm,
    ParametroForm,
    RolForm,
    SalarioForm,
)
from estimacion.models import TipoCostoFabricacion
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
    archivados = request.GET.get("archivados") == "1"
    estimaciones = servicio.estimaciones(
        request.user, juego_id, incluir_eliminadas=archivados
    )
    rondas = list(juego.rondas.all())
    rondas_cerradas = {ronda.numero for ronda in rondas if ronda.cerrada}
    for estimacion in estimaciones:
        estimacion.puede_editar = (
            not estimacion.eliminada
            and estimacion.ronda not in rondas_cerradas
        )
        estimacion.puede_restaurar = (
            estimacion.eliminada
            and estimacion.ronda not in rondas_cerradas
        )
    ronda_actual = _ronda_actual(request, juego, fases)
    consolidacion = _consolidacion(request, servicio, juego, ronda_actual)
    versiones = list(crear_presupuesto_service().versiones(
        request.user, juego_id, incluir_eliminadas=archivados,
    ))
    presupuesto_service = crear_presupuesto_service()
    for version in versiones:
        version.total_estimado = presupuesto_service.total(version)
    costos_fabricacion = list(
        servicio.costos_fabricacion(request.user, juego_id)
    )
    form = extra.get("form")
    if isinstance(form, EstimacionMatrizForm):
        _adjuntar_filas_matriz(form, fases)
    contexto.update(
        juego=juego,
        fases=fases,
        roles=catalogos["roles"],
        expertos=catalogos["expertos"],
        estimaciones=estimaciones,
        rondas=rondas,
        ronda_actual=ronda_actual,
        consolidacion=consolidacion,
        versiones=versiones,
        costos_fabricacion=costos_fabricacion,
        archivados=archivados,
        **extra,
    )
    return contexto


def _adjuntar_filas_matriz(form, fases):
    """Campos PERT ligados a cada fase para la tabla del modal."""
    form.filas = [
        {
            "fase": fase,
            "optimista": form[f"fase_{fase.pk}_optimista"],
            "moda": form[f"fase_{fase.pk}_moda"],
            "pesimista": form[f"fase_{fase.pk}_pesimista"],
        }
        for fase in fases
    ]


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
        try:
            servicio.crear_juego(request.user, form.cleaned_data["nombre"])
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


def _ronda_registro(juego):
    """Ronda activa de captura: la última abierta, o la siguiente si la
    anterior ya está cerrada (una ronda nueva por cada cierre Delphi)."""
    numeros = [r.numero for r in juego.rondas.all()]
    abiertas = [r.numero for r in juego.rondas.all() if not r.cerrada]
    if abiertas:
        return max(abiertas)
    return max(numeros) + 1 if numeros else 1


@login_required
@require_http_methods(["GET", "POST"])
def estimacion_nueva(request, juego_id):
    """Matriz PERT: un experto y rol estiman todas las fases."""
    servicio = crear_estimacion_service()
    try:
        juego = servicio.obtener_juego(request.user, juego_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    fases = list(juego.fases.all())
    ronda = _ronda_registro(juego)
    if request.method != "POST":
        return render(
            request, JUEGO_TEMPLATE,
            _contexto_juego(
                request, juego_id, servicio,
                form=EstimacionMatrizForm(fases=fases),
                ronda_registro=ronda,
            ),
        )
    form = EstimacionMatrizForm(request.POST, fases=fases)
    if form.is_valid():
        datos = form.cleaned_data
        matriz = {
            fase.pk: {
                "optimista": datos[f"fase_{fase.pk}_optimista"],
                "moda": datos[f"fase_{fase.pk}_moda"],
                "pesimista": datos[f"fase_{fase.pk}_pesimista"],
            }
            for fase in fases
        }
        try:
            servicio.registrar_estimacion_matriz(
                request.user,
                juego_id=juego_id,
                rol_id=datos["rol"],
                experto_id=datos["experto"],
                ronda=ronda,
                matriz=matriz,
                justificacion=datos["justificacion"],
            )
        except UsuarioError as error:
            raise _sin_permiso(error) from error
        except EstimacionError as error:
            form.add_error(None, str(error))
        else:
            messages.success(
                request,
                f"Estimación registrada para {len(matriz)} fases "
                f"en la ronda {ronda}.",
            )
            return redirect("estimacion_juego", juego_id=juego_id)
    return render(
        request, JUEGO_TEMPLATE,
        _contexto_juego(
            request, juego_id, servicio, form=form,
            ronda_registro=ronda,
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def estimacion_editar(request, juego_id, estimacion_id):
    servicio = crear_estimacion_service()
    try:
        estimacion = servicio.obtener_estimacion(
            request.user, juego_id, estimacion_id
        )
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
        return redirect("estimacion_juego", juego_id=juego_id)

    initial = {
        "optimista": estimacion.optimista,
        "moda": estimacion.moda,
        "pesimista": estimacion.pesimista,
        "justificacion": estimacion.justificacion,
    }
    form = EstimacionExpertoEdicionForm(
        request.POST if request.method == "POST" else None,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        try:
            servicio.actualizar_estimacion(
                request.user, juego_id, estimacion_id,
                **form.cleaned_data,
            )
        except UsuarioError as error:
            raise _sin_permiso(error) from error
        except EstimacionError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, "Estimación experta actualizada.")
            return redirect("estimacion_juego", juego_id=juego_id)
    return render(
        request, JUEGO_TEMPLATE,
        _contexto_juego(
            request, juego_id, servicio,
            form_edicion_estimacion=form,
            estimacion_objetivo=estimacion,
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def estimacion_eliminar(request, juego_id, estimacion_id):
    servicio = crear_estimacion_service()
    try:
        estimacion = servicio.obtener_estimacion(
            request.user, juego_id, estimacion_id
        )
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
        return redirect("estimacion_juego", juego_id=juego_id)

    form = ConfirmarBajaForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        try:
            servicio.eliminar_estimacion(
                request.user, juego_id, estimacion_id
            )
        except UsuarioError as error:
            raise _sin_permiso(error) from error
        except EstimacionError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, "Estimación archivada.")
            return redirect("estimacion_juego", juego_id=juego_id)
    return render(
        request, JUEGO_TEMPLATE,
        _contexto_juego(
            request, juego_id, servicio,
            form_baja_estimacion=form,
            estimacion_objetivo=estimacion,
        ),
    )


@login_required
@require_POST
def estimacion_restaurar(request, juego_id, estimacion_id):
    try:
        crear_estimacion_service().restaurar_estimacion(
            request.user, juego_id, estimacion_id
        )
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Estimación restaurada.")
    return redirect(
        f"{reverse('estimacion_juego', args=[juego_id])}?archivados=1"
    )


def _fases_del_juego(request, servicio, juego_id):
    try:
        juego = servicio.obtener_juego(request.user, juego_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    return list(juego.fases.all())


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


@login_required
@require_http_methods(["GET", "POST"])
def version_eliminar(request, version_id):
    servicio = crear_presupuesto_service()
    try:
        version = servicio.obtener_version(request.user, version_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
        return redirect("estimacion")

    form = ConfirmarBajaForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        try:
            servicio.eliminar_version(request.user, version_id)
        except UsuarioError as error:
            raise _sin_permiso(error) from error
        except EstimacionError as error:
            form.add_error(None, str(error))
        else:
            messages.success(
                request, f"Versión {version.numero} archivada; se conservó "
                "su historial y cualquier vínculo con órdenes."
            )
            return redirect("estimacion_juego", juego_id=version.juego_id)
    return render(
        request, JUEGO_TEMPLATE,
        _contexto_juego(
            request, version.juego_id, crear_estimacion_service(),
            resumen_version=version, accion="eliminar",
            form_baja_version=form,
        ),
    )


@login_required
@require_POST
def version_restaurar(request, version_id):
    try:
        version = crear_presupuesto_service().restaurar_version(
            request.user, version_id
        )
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
        return redirect("estimacion")
    messages.success(request, f"Versión {version.numero} restaurada.")
    return redirect(
        f"{reverse('estimacion_juego', args=[version.juego_id])}"
        "?archivados=1"
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
@require_http_methods(["GET", "POST"])
def juego_costo_directo(request, juego_id):
    return _juego_costo(
        request, juego_id, crear_estimacion_service(),
        TipoCostoFabricacion.DIRECTO,
    )


@login_required
@require_http_methods(["GET", "POST"])
def juego_costo_indirecto(request, juego_id):
    return _juego_costo(
        request, juego_id, crear_estimacion_service(),
        TipoCostoFabricacion.INDIRECTO,
    )


def _juego_costo(request, juego_id, servicio, tipo):
    """Costo directo/indirecto de fabricación estimado del juego."""
    if request.method == "POST":
        form = CostoForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                servicio.agregar_costo_fabricacion(
                    request.user, juego_id, tipo,
                    datos["concepto"], datos["monto"],
                )
            except UsuarioError as error:
                raise _sin_permiso(error) from error
            except EstimacionError as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, "Costo de fabricación registrado.")
                return redirect("estimacion_juego", juego_id=juego_id)
        return render(
            request, JUEGO_TEMPLATE,
            _contexto_juego(
                request, juego_id, servicio,
                form_fab=form, fab_tipo=tipo,
            ),
        )
    return render(
        request, JUEGO_TEMPLATE,
        _contexto_juego(
            request, juego_id, servicio,
            form_fab=CostoForm(), fab_tipo=tipo,
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def version_rechazar(request, version_id):
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
                resumen_version=version, accion="rechazar",
            ),
        )
    try:
        servicio.rechazar(request.user, version_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request, f"Versión {version.numero} rechazada."
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


@login_required
@require_http_methods(["GET", "POST"])
def catalogo_rol_editar(request, rol_id):
    servicio = crear_estimacion_service()
    try:
        rol = servicio.obtener_rol(request.user, rol_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
        return redirect("estimacion_catalogos")
    if request.method == "POST":
        form = RolForm(request.POST)
        if form.is_valid():
            try:
                servicio.actualizar_rol(
                    request.user, rol_id,
                    form.cleaned_data["nombre"],
                    form.cleaned_data["nivel"],
                )
            except UsuarioError as error:
                raise _sin_permiso(error) from error
            except EstimacionError as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, "Rol actualizado.")
                return redirect("estimacion_catalogos")
        return _render_catalogo(
            request, servicio, form=form, tipo="rol_editar",
            rol_editar=rol,
        )
    return _render_catalogo(
        request, servicio,
        form=RolForm(initial={"nombre": rol.nombre, "nivel": rol.nivel}),
        tipo="rol_editar", rol_editar=rol,
    )


@login_required
@require_http_methods(["GET", "POST"])
def catalogo_experto_editar(request, experto_id):
    servicio = crear_estimacion_service()
    try:
        experto = servicio.obtener_experto(request.user, experto_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
        return redirect("estimacion_catalogos")
    if request.method == "POST":
        form = ExpertoForm(request.POST)
        if form.is_valid():
            try:
                servicio.actualizar_experto(
                    request.user, experto_id, form.cleaned_data["nombre"]
                )
            except UsuarioError as error:
                raise _sin_permiso(error) from error
            except EstimacionError as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, "Experto actualizado.")
                return redirect("estimacion_catalogos")
        return _render_catalogo(
            request, servicio, form=form, tipo="experto_editar",
            experto_editar=experto,
        )
    return _render_catalogo(
        request, servicio,
        form=ExpertoForm(initial={"nombre": experto.nombre}),
        tipo="experto_editar", experto_editar=experto,
    )


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


def _render_catalogo(request, servicio, *, form=None, tipo=None, **contexto_extra):
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
        "rol_editar": "form_rol_editar",
        "experto_editar": "form_experto_editar",
        "parametro_editar": "form_parametro_editar",
        "salario_editar": "form_salario_editar",
    }.get(tipo)
    if clave:
        extras[clave] = form
    extras.update(contexto_extra)
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
def catalogo_parametro_editar(request, parametro_id):
    servicio = crear_estimacion_service()
    try:
        parametro = servicio.obtener_parametro(request.user, parametro_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
        return redirect("estimacion_catalogos")
    initial = {
        "valor": parametro.valor,
        "vigente_desde": parametro.vigente_desde,
        "vigente_hasta": parametro.vigente_hasta,
        "verificado": parametro.verificado,
    }
    if request.method == "POST":
        form = ParametroEdicionForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                servicio.actualizar_parametro(
                    request.user, parametro_id,
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
                messages.success(request, "Parámetro actualizado.")
                return redirect("estimacion_catalogos")
        return _render_catalogo(
            request, servicio, form=form, tipo="parametro_editar",
            parametro_editar=parametro,
        )
    return _render_catalogo(
        request, servicio,
        form=ParametroEdicionForm(initial=initial),
        tipo="parametro_editar", parametro_editar=parametro,
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


@login_required
@require_http_methods(["GET", "POST"])
def catalogo_salario_editar(request, salario_id):
    servicio = crear_estimacion_service()
    try:
        salario = servicio.obtener_salario(request.user, salario_id)
    except UsuarioError as error:
        raise _sin_permiso(error) from error
    except EstimacionError as error:
        messages.error(request, str(error))
        return redirect("estimacion_catalogos")
    if request.method == "POST":
        form = SalarioForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                servicio.actualizar_salario(
                    request.user, salario_id,
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
                messages.success(request, "Salario actualizado.")
                return redirect("estimacion_catalogos")
        return _render_catalogo(
            request, servicio, form=form, tipo="salario_editar",
            salario_editar=salario,
        )
    return _render_catalogo(
        request, servicio,
        form=SalarioForm(initial={
            "rol": salario.rol_id,
            "salario_bruto": salario.salario_bruto,
            "vigente_desde": salario.vigente_desde,
            "vigente_hasta": salario.vigente_hasta,
        }),
        tipo="salario_editar", salario_editar=salario,
    )
