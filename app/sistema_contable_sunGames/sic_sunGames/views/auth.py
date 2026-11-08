from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from usuarios.composition import (
    crear_acceso_service,
    crear_autenticacion_service,
)
from usuarios.exceptions import AreaInicialPendienteError, UsuarioError

from ..forms import LoginForm

LOGIN_TEMPLATE = "sic_sunGames/login.html"


def login_view(request):
    if request.user.is_authenticated:
        return _area_inicial(request)
    if request.method != "POST":
        return render(request, LOGIN_TEMPLATE, {"form": LoginForm()})

    form = LoginForm(request.POST)
    servicio = crear_autenticacion_service()
    if not form.is_valid():
        servicio.registrar_intento_incompleto(
            form.data.get("username", "").strip()
        )
        return render(request, LOGIN_TEMPLATE, {"form": form})

    username = form.cleaned_data["username"]
    try:
        servicio.iniciar_sesion(
            request, username, form.cleaned_data["password"]
        )
    except UsuarioError as error:
        return render(
            request,
            LOGIN_TEMPLATE,
            {
                "form": LoginForm(initial={"username": username}),
                "error": str(error),
            },
        )
    return _area_inicial(request)


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


def _area_inicial(request):
    try:
        return redirect(crear_acceso_service().area_inicial(request.user))
    except AreaInicialPendienteError as aviso:
        return render(request, LOGIN_TEMPLATE, {"aviso": str(aviso)})
