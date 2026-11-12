from django.urls import path

from apps.m14_proveedores.admin_views import (
    ProveedorAdminDetailView,
    ProveedorAdminListCreateView,
    ProveedoresActivosAdminView,
)

urlpatterns = [
    path("", ProveedorAdminListCreateView.as_view(), name="proveedores-admin"),
    path("activos/", ProveedoresActivosAdminView.as_view(), name="proveedores-activos"),
    path("<int:pk>/", ProveedorAdminDetailView.as_view(), name="proveedor-admin-detalle"),
]
