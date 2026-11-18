from django.urls import path

from . import views

urlpatterns = [
    path("", views.ordenes, name="costos_ordenes"),
    path("nueva/", views.orden_nueva, name="costos_orden_nueva"),
    path("catalogos/", views.catalogos, name="costos_catalogos"),
    path("catalogos/proceso/nuevo/", views.proceso_nuevo,
         name="costos_proceso_nuevo"),
    path("catalogos/proceso/<int:proceso_id>/", views.proceso_editar,
         name="costos_proceso_editar"),
    path("catalogos/cuentas/<str:elemento>/", views.configuracion_editar,
         name="costos_configuracion_editar"),
    path("<int:orden_id>/", views.orden_detalle, name="costos_orden"),
    path("<int:orden_id>/registros/<slug:tipo>/nuevo/",
         views.registro_nuevo, name="costos_registro_nuevo"),
    path("<int:orden_id>/registros/<int:registro_id>/anular/",
         views.registro_anular, name="costos_registro_anular"),
]
