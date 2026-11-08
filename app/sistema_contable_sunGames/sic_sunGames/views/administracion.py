"""Pantallas del Administrador: CU-02 Usuarios y CU-03 Auditoría."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from bitacora.exceptions import AuditoriaError
from usuarios.composition import (
    crear_auditoria_service,
    crear_usuario_service,
)
from usuarios.exceptions import (
    RolInvalidoError,
    RolNoAutorizadoError,
    UsuarioDuplicadoError,
    UsuarioError,
    UsuarioInactivoError,
    UsuarioNoEncontradoError,
)
from usuarios.forms import UsuarioAltaForm

from .pages import contexto_panel

USUARIOS_TEMPLATE = "sic_sunGames/usuarios.html"
AUDITORIA_TEMPLATE = "sic_sunGames/auditoria.html"
REGISTROS_POR_PAGINA = 20


def _sin_permiso(error):
    return PermissionDenied(str(error))


def _pagina(request, registros):
    return Paginator(registros, REGISTROS_POR_PAGINA).get_page(
        request.GET.get("pagina")
    )


def _render_usuarios(request, servicio, **extra):
    try:
        usuarios = servicio.listar(request.user)
    except (RolNoAutorizadoError, UsuarioInactivoError) as error:
        raise _sin_permiso(error) from error
    contexto = contexto_panel(request, "users")
    contexto.update(pagina=_pagina(request, usuarios), **extra)
    return render(request, USUARIOS_TEMPLATE, contexto)


@login_required
def usuarios(request):
    return _render_usuarios(request, crear_usuario_service())


@login_required
@require_http_methods(["GET", "POST"])
def usuario_nuevo(request):
    servicio = crear_usuario_service()
    if request.method != "POST":
        contexto_panel(request, "users")
        return _render_usuarios(request, servicio, form=UsuarioAltaForm())

    form = UsuarioAltaForm(request.POST)
    if form.is_valid():
        try:
            usuario = servicio.agregar(request.user, **form.cleaned_data)
        except (RolNoAutorizadoError, UsuarioInactivoError) as error:
            raise _sin_permiso(error) from error
        except UsuarioDuplicadoError as error:
            form.add_error("username", str(error))
        except RolInvalidoError as error:
            form.add_error("rol", str(error))
        else:
            messages.success(
                request, f"Usuario {usuario.username} agregado."
            )
            return redirect("users")
    return _render_usuarios(request, servicio, form=form)


@login_required
def usuario_detalle(request, username):
    servicio = crear_usuario_service()
    try:
        ficha = servicio.obtener(request.user, username)
    except (RolNoAutorizadoError, UsuarioInactivoError) as error:
        raise _sin_permiso(error) from error
    except UsuarioNoEncontradoError as error:
        messages.error(request, str(error))
        return redirect("users")
    return _render_usuarios(request, servicio, ficha=ficha)


@login_required
@require_http_methods(["GET", "POST"])
def usuario_desactivar(request, username):
    servicio = crear_usuario_service()
    try:
        if request.method != "POST":
            resumen = servicio.obtener(request.user, username)
            return _render_usuarios(request, servicio, resumen=resumen)
        servicio.desactivar(request.user, username)
    except RolNoAutorizadoError as error:
        raise _sin_permiso(error) from error
    except UsuarioError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Usuario {username} desactivado.")
    return redirect("users")


@login_required
def auditoria(request):
    servicio = crear_auditoria_service()
    try:
        eventos = servicio.listar(request.user)
    except (RolNoAutorizadoError, UsuarioInactivoError) as error:
        raise _sin_permiso(error) from error
    contexto = contexto_panel(request, "audit")
    contexto["pagina"] = _pagina(request, eventos)
    return render(request, AUDITORIA_TEMPLATE, contexto)


@login_required
def auditoria_descargar(request, formato):
    servicio = crear_auditoria_service()
    try:
        archivo = servicio.exportar(request.user, formato)
    except (RolNoAutorizadoError, UsuarioInactivoError) as error:
        raise _sin_permiso(error) from error
    except AuditoriaError as error:
        messages.warning(request, str(error))
        return redirect("audit")
    respuesta = HttpResponse(
        archivo.contenido, content_type=archivo.tipo_contenido
    )
    respuesta["Content-Disposition"] = (
        f'attachment; filename="{archivo.nombre}"'
    )
    return respuesta
