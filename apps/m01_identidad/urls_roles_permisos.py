from django.urls import path

from apps.m01_identidad.admin_roles_views import (
    MatrizPermisosView,
    PermisoCatalogosView,
    PermisoDetailView,
    PermisoListCreateView,
    RolDetailView,
    RolesActivosCatalogoView,
    RolListCreateView,
    UsuariosActivosCatalogoView,
)

urlpatterns = [
    path("roles", RolListCreateView.as_view(), name="roles-list"),
    path("roles/<int:id_rol>", RolDetailView.as_view(), name="roles-detail"),
    path("roles/catalogo/activos", RolesActivosCatalogoView.as_view(), name="roles-activos"),
    path("permisos", PermisoListCreateView.as_view(), name="permisos-list"),
    path("permisos/catalogos", PermisoCatalogosView.as_view(), name="permisos-catalogos"),
    path("permisos/<int:id_permiso>", PermisoDetailView.as_view(), name="permisos-detail"),
    path("matriz", MatrizPermisosView.as_view(), name="matriz-permisos"),
    path("usuarios-activos", UsuariosActivosCatalogoView.as_view(), name="matriz-usuarios"),
]
