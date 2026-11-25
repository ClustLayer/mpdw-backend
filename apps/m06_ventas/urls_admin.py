from django.urls import path

from apps.m06_ventas.admin_facturacion_externa_views import (
    FacturacionExternaBandejaView,
    FacturacionExternaDetalleView,
    FacturacionExternaEstadoView,
    FacturacionExternaSoporteView,
)
from apps.m06_ventas.admin_views import (
    FacturaAnularView,
    FacturaDetailView,
    FacturaDevolucionView,
    FacturasEstadisticasView,
    FacturasListView,
    PosBuscarProductosView,
    PosCatalogosView,
    PosEmitirView,
)

urlpatterns = [
    path("pos/catalogos/", PosCatalogosView.as_view(), name="pos-catalogos"),
    path("pos/productos/", PosBuscarProductosView.as_view(), name="pos-buscar-productos"),
    path("pos/emitir/", PosEmitirView.as_view(), name="pos-emitir"),
    path("facturas/estadisticas/", FacturasEstadisticasView.as_view(), name="facturas-estadisticas"),
    path("facturas/", FacturasListView.as_view(), name="facturas-list"),
    path("facturas/<int:pk>/", FacturaDetailView.as_view(), name="facturas-detail"),
    path("facturas/<int:pk>/anular/", FacturaAnularView.as_view(), name="facturas-anular"),
    path(
        "facturas/<int:pk>/devolucion/", FacturaDevolucionView.as_view(), name="facturas-devolucion"
    ),
    path(
        "facturacion-externa/",
        FacturacionExternaBandejaView.as_view(),
        name="facturacion-externa-bandeja",
    ),
    path(
        "facturacion-externa/<int:pk>/",
        FacturacionExternaDetalleView.as_view(),
        name="facturacion-externa-detalle",
    ),
    path(
        "facturacion-externa/<int:pk>/soporte/",
        FacturacionExternaSoporteView.as_view(),
        name="facturacion-externa-soporte",
    ),
    path(
        "facturacion-externa/<int:pk>/estado/",
        FacturacionExternaEstadoView.as_view(),
        name="facturacion-externa-estado",
    ),
]
