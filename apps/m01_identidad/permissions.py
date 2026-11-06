# ==============================================================================
# Clase de Permiso Dinámico para DRF - MPDW
# SAD Ref: ADR-007, §10.4, BR-10
# ==============================================================================
from rest_framework.permissions import BasePermission

from apps.m01_identidad.services import PermissionService
from contratos.dtos import AuthContext


class HasDynamicPermission(BasePermission):
    """Evalúa los permisos en servidor contra la matriz Usuario_permiso / Rol_permiso."""

    def __init__(self, service: PermissionService | None = None) -> None:
        self._service = service or PermissionService()

    def has_permission(self, request, view) -> bool:
        required_permission = getattr(view, "required_permission", None)
        if not required_permission:
            return True

        modulo, accion = required_permission
        ctx: AuthContext | None = getattr(request, "auth_context", None)
        if not ctx:
            return False

        return self._service.tiene_permiso(ctx, modulo, accion)
