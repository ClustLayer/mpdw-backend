# Correcciones iteración 7 — Épica 2 y 3 (backend)

**Rama:** `epica-3-ajustes-y-fixes`

## Cambios

- `permiso_eval.py`: catálogo con **Sin acceso** y **Total**; aliases para evaluación.
- `PermissionRepository`: bloqueo por Sin acceso; `acciones_por_modulo` normalizado.
- `PermissionService.accesos_panel`: omite módulos solo con Sin acceso.
- `AdminRolesPermisosService.eliminar_rol` + `DELETE` en `RolDetailView`.
- OpenAPI regenerado (`docs/openapi.yaml`).

## Pruebas

- `tests/unit/test_permiso_eval.py`, `test_permiso_repository.py`
- Ampliación `test_epic3_roles_permisos.py`, `test_epic3_roles_views.py`

## Calidad

- `make calidad` en verde.
