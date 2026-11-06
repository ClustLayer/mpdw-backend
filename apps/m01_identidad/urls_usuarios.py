from django.urls import path

from apps.m01_identidad.admin_views import (
    RolesCatalogoView,
    UsuarioContrasenaTemporalView,
    UsuarioDetailView,
    UsuarioEstadoView,
    UsuarioListCreateView,
)

urlpatterns = [
    path("", UsuarioListCreateView.as_view(), name="usuarios-list-create"),
    path("roles", RolesCatalogoView.as_view(), name="usuarios-roles"),
    path("<int:id_usuario>", UsuarioDetailView.as_view(), name="usuarios-detail"),
    path("<int:id_usuario>/estado", UsuarioEstadoView.as_view(), name="usuarios-estado"),
    path("<int:id_usuario>/contrasena-temporal", UsuarioContrasenaTemporalView.as_view(), name="usuarios-contrasena-temporal"),
]
