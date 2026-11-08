from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse

from usuarios.composition import crear_acceso_service
from usuarios.exceptions import UsuarioError


SCREEN_URL_NAMES = {
    "dashboard": "dashboard",
    "ledger": "ledger",
    "accounts": "accounts",
    "reports": "reports",
    "operations": "operations",
    "users": "users",
    "audit": "audit",
}


def index(request):
    return redirect("login")


@login_required
def panel(request):
    return redirect("login")


def contexto_panel(request, screen):
    """Verifica el acceso al módulo y arma el contexto común del panel."""
    acceso = crear_acceso_service()
    try:
        acceso.verificar_acceso(request.user, screen)
    except UsuarioError as error:
        raise PermissionDenied(str(error)) from error

    screen_urls = {
        "login": reverse("login"),
        "logout": reverse("logout"),
        **{
            name: reverse(route_name)
            for name, route_name in SCREEN_URL_NAMES.items()
        },
    }
    return {
        "initial_screen": screen,
        "screen_urls": screen_urls,
        "logo_url": static("sic_sunGames/SunGames_Logo.png"),
        "modulos": sorted(acceso.modulos(request.user)),
        "usuario_actual": {
            "name": request.user.nombre_completo,
            "role": request.user.get_rol_display(),
        },
    }


@login_required
def render_screen(request, screen):
    if screen not in SCREEN_URL_NAMES:
        raise Http404
    return render(
        request, "sic_sunGames/index.html", contexto_panel(request, screen)
    )
