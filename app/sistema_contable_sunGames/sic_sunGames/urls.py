from django.urls import path

from .views import administracion, auth, catalogo, estados, mayor, pages

urlpatterns = [
    path("", pages.index, name="index"),
    path("login/", auth.login_view, name="login"),
    path("panel/", pages.panel, name="panel"),
    path("logout/", auth.logout_view, name="logout"),
    path("panel/dashboard/", pages.render_screen, {"screen": "dashboard"}, name="dashboard"),
    path("panel/libro-mayor/", mayor.libro_mayor, name="ledger"),
    path("panel/libro-mayor/balance/pdf/", mayor.balance_pdf, name="balance_pdf"),
    path("panel/libro-mayor/registrar/", mayor.registrar_transaccion, name="transaccion_registrar"),
    path("panel/catalogo-cuentas/", catalogo.cuentas, name="accounts"),
    path("panel/catalogo-cuentas/nueva/", catalogo.cuenta_nueva, name="cuenta_nueva"),
    path("panel/catalogo-cuentas/siguiente-codigo/", catalogo.cuenta_siguiente_codigo, name="cuenta_siguiente_codigo"),
    path("panel/catalogo-cuentas/<str:codigo>/", catalogo.cuenta_detalle, name="cuenta_detalle"),
    path("panel/catalogo-cuentas/<str:codigo>/modificar/", catalogo.cuenta_modificar, name="cuenta_modificar"),
    path("panel/estados-financieros/", pages.render_screen, {"screen": "reports"}, name="reports"),
    path("panel/estados-financieros/periodos/", estados.cierre_periodos, name="cierre_periodos"),
    path("panel/estados-financieros/periodos/<int:periodo_id>/cerrar/", estados.cerrar_periodo, name="periodo_cerrar"),
    path("panel/estados-financieros/periodos/<int:periodo_id>/reabrir/", estados.reabrir_periodo, name="periodo_reabrir"),
    path("panel/estados-financieros/<int:periodo_id>/<str:tipo>/pdf/", estados.estado_pdf, name="estado_pdf"),
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
