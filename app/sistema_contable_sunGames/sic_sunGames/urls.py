from django.urls import path

from .views import administracion, auth, pages

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
    path("panel/usuarios/", administracion.usuarios, name="users"),
    path("panel/usuarios/nuevo/", administracion.usuario_nuevo, name="usuario_nuevo"),
    path("panel/usuarios/<str:username>/", administracion.usuario_detalle, name="usuario_detalle"),
    path("panel/usuarios/<str:username>/desactivar/", administracion.usuario_desactivar, name="usuario_desactivar"),
    path("panel/usuarios/<str:username>/reactivar/", administracion.usuario_reactivar, name="usuario_reactivar"),
    path("panel/usuarios/<str:username>/contrasena/", administracion.usuario_contrasena, name="usuario_contrasena"),
    path("panel/auditoria/", administracion.auditoria, name="audit"),
    path("panel/auditoria/descargar/<str:formato>/", administracion.auditoria_descargar, name="auditoria_descargar"),
]
