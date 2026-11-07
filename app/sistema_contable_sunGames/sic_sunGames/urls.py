from django.urls import path

from .views import auth, pages

urlpatterns = [
    path("", pages.index, name="index"),
    path("login/", auth.login_view, name="login"),
    path("panel/", pages.panel, name="panel"),
    path("logout/", auth.logout_view, name="logout"),
    path("panel/dashboard/", pages.render_screen, {"screen": "dashboard"}, name="dashboard"),
    path("panel/libro-mayor/", pages.render_screen, {"screen": "ledger"}, name="ledger"),
    path("panel/catalogo-cuentas/", pages.render_screen, {"screen": "accounts"}, name="accounts"),
    path("panel/estados-financieros/", pages.render_screen, {"screen": "reports"}, name="reports"),
    path("panel/ventas-costos/", pages.render_screen, {"screen": "operations"}, name="operations"),
    path("panel/usuarios/", pages.render_screen, {"screen": "users"}, name="users"),
    path("panel/auditoria/", pages.render_screen, {"screen": "audit"}, name="audit"),
]
