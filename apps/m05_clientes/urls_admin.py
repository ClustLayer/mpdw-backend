from django.urls import path

from apps.m05_clientes.admin_views import (
    ClienteAdminDetailView,
    ClienteAdminListCreateView,
    ClienteHistorialView,
    ClienteTelefonoCheckView,
    TipoClienteAdminView,
    TipoClienteDetalleView,
)

urlpatterns = [
    path("", ClienteAdminListCreateView.as_view(), name="clientes-admin"),
    path("verificar-telefono/", ClienteTelefonoCheckView.as_view(), name="clientes-verificar-telefono"),
    path("tipos/", TipoClienteAdminView.as_view(), name="tipos-cliente"),
    path("tipos/<int:pk>/", TipoClienteDetalleView.as_view(), name="tipos-cliente-detalle"),
    path("<int:pk>/", ClienteAdminDetailView.as_view(), name="cliente-admin-detalle"),
    path("<int:pk>/historial/", ClienteHistorialView.as_view(), name="cliente-historial"),
]
