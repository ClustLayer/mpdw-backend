from django.urls import path

from apps.m07_domicilios.admin_views import (
    DomicilioAsignarView,
    DomicilioBandejaView,
    DomicilioCreateView,
    DomicilioDetalleView,
    DomicilioEstadoView,
    DomicilioPrecargaFacturaView,
    HistorialMensajeriaView,
    MensajeroDetailView,
    MensajeroListCreateView,
    MensajerosActivosView,
)

urlpatterns = [
    path("bandeja/", DomicilioBandejaView.as_view(), name="domicilios-bandeja"),
    path("historial/", HistorialMensajeriaView.as_view(), name="domicilios-historial"),
    path("mensajeros/activos/", MensajerosActivosView.as_view(), name="mensajeros-activos"),
    path("mensajeros/", MensajeroListCreateView.as_view(), name="mensajeros-list-create"),
    path("mensajeros/<int:id_mensajero>/", MensajeroDetailView.as_view(), name="mensajeros-detalle"),
    path("factura/<int:id_factura>/precarga/", DomicilioPrecargaFacturaView.as_view(), name="domicilios-precarga"),
    path("", DomicilioCreateView.as_view(), name="domicilios-crear"),
    path("<int:id_entrega>/asignar/", DomicilioAsignarView.as_view(), name="domicilios-asignar"),
    path("<int:id_entrega>/estado/", DomicilioEstadoView.as_view(), name="domicilios-estado"),
    path("<int:id_entrega>/", DomicilioDetalleView.as_view(), name="domicilios-detalle"),
]
