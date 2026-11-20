from django.urls import path

from apps.m11_eventos.admin_views import (
    EventoAdminDetailView,
    EventoAdminListCreateView,
    EventoImagenView,
    EventosPublicosView,
    SedesActivasEventosView,
)

urlpatterns = [
    path("publicos/", EventosPublicosView.as_view(), name="eventos-publicos"),
    path("sedes-activas/", SedesActivasEventosView.as_view(), name="eventos-sedes-activas"),
    path("", EventoAdminListCreateView.as_view(), name="eventos-admin"),
    path("<int:pk>/imagen/", EventoImagenView.as_view(), name="evento-imagen"),
    path("<int:pk>/", EventoAdminDetailView.as_view(), name="evento-admin-detalle"),
]
