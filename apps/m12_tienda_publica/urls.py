from django.urls import path

from apps.m12_tienda_publica.views import (
    TiendaCatalogoView,
    TiendaContactoWhatsappView,
    TiendaEscaparatesView,
    TiendaFiltrosView,
    TiendaPrepararPedidoView,
    TiendaProductoDetalleView,
    TiendaSedesView,
    TiendaValidarCarritoView,
)

urlpatterns = [
    path("escaparates/", TiendaEscaparatesView.as_view(), name="tienda-escaparates"),
    path("filtros/", TiendaFiltrosView.as_view(), name="tienda-filtros"),
    path("catalogo/", TiendaCatalogoView.as_view(), name="tienda-catalogo"),
    path("productos/<slug:slug>/", TiendaProductoDetalleView.as_view(), name="tienda-producto"),
    path("carrito/validar/", TiendaValidarCarritoView.as_view(), name="tienda-validar-carrito"),
    path("sedes/", TiendaSedesView.as_view(), name="tienda-sedes"),
    path("whatsapp/contacto/", TiendaContactoWhatsappView.as_view(), name="tienda-whatsapp-contacto"),
    path("pedidos/preparar/", TiendaPrepararPedidoView.as_view(), name="tienda-pedido-preparar"),
]
