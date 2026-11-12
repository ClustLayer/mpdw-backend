from django.urls import path

from apps.m04_inventario.admin_views import (
    EntradaLoteView,
    ExistenciasView,
    KardexView,
    MovimientoView,
    ProductosOpcionesView,
)

urlpatterns = [
    path("existencias/", ExistenciasView.as_view(), name="inventario-existencias"),
    path("kardex/", KardexView.as_view(), name="inventario-kardex"),
    path("productos-opciones/", ProductosOpcionesView.as_view(), name="inventario-productos-opciones"),
    path("movimientos/entrada-lote/", EntradaLoteView.as_view(), name="inventario-entrada-lote"),
    path("movimientos/<str:accion>/", MovimientoView.as_view(), name="inventario-movimiento"),
]
