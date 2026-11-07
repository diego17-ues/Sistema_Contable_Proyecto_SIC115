from django.http import Http404
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse


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


def panel(request):
    return redirect("dashboard")


def render_screen(request, screen):
    if screen != "login" and screen not in SCREEN_URL_NAMES:
        raise Http404

    screen_urls = {
        "login": reverse("login"),
        "logout": reverse("logout"),
        **{name: reverse(route_name) for name, route_name in SCREEN_URL_NAMES.items()},
    }
    return render(
        request,
        "sic_sunGames/index.html",
        {
            "initial_screen": screen,
            "screen_urls": screen_urls,
            "logo_url": static("sic_sunGames/SunGames_Logo.png"),
        },
    )
