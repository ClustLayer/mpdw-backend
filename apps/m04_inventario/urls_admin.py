from django.urls import path

from apps.m04_inventario.admin_views import ExistenciasView, KardexView, MovimientoView

urlpatterns = [
    path("existencias/", ExistenciasView.as_view(), name="inventario-existencias"),
    path("kardex/", KardexView.as_view(), name="inventario-kardex"),
    path("movimientos/<str:accion>/", MovimientoView.as_view(), name="inventario-movimiento"),
]
