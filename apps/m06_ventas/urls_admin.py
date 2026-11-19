from django.urls import path

from apps.m06_ventas.admin_views import (
    FacturaAnularView,
    FacturaDetailView,
    FacturaDevolucionView,
    FacturasListView,
    PosBuscarProductosView,
    PosCatalogosView,
    PosEmitirView,
)

urlpatterns = [
    path("pos/catalogos/", PosCatalogosView.as_view(), name="pos-catalogos"),
    path("pos/productos/", PosBuscarProductosView.as_view(), name="pos-buscar-productos"),
    path("pos/emitir/", PosEmitirView.as_view(), name="pos-emitir"),
    path("facturas/", FacturasListView.as_view(), name="facturas-list"),
    path("facturas/<int:pk>/", FacturaDetailView.as_view(), name="facturas-detail"),
    path("facturas/<int:pk>/anular/", FacturaAnularView.as_view(), name="facturas-anular"),
    path(
        "facturas/<int:pk>/devolucion/", FacturaDevolucionView.as_view(), name="facturas-devolucion"
    ),
]
