# Correcciones iteracion 6 — Epica 2

**Fecha:** 2026-11-05  
**Alcance:** HU_MPDW_01_07 a HU_MPDW_01_12

## Entregables
- Migracion `0006_epic2_perfil_usuarios` (apellido, telefono, contrasena_temporal_expira, version_fila).
- API `/api/v1/usuarios/` con listado, creacion, detalle, edicion, estado y contraseña temporal.
- PATCH `/api/v1/auth/profile` para mi perfil (HU 12).
- Correo de contraseña inicial al crear usuario (B-18).
- OpenAPI regenerado; `make calidad` en verde (cobertura >= 90%).

## Trazabilidad pruebas
- `tests/unit/test_epic2_usuarios.py`
- `tests/integration/test_epic2_usuarios_api.py`
