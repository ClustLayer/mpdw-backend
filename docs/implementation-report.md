# Implementation report

## Epica 1 — Autenticacion y seguridad de sesion
**Status:** COMPLETED
**Date:** 2026-11-04

### Analysis (orchestrator)
- project_mode backend: EXTEND_EXISTING. El modulo `m01_identidad` ya emitia JWT y refresh opaco.
- project_mode frontend: MOCKUP_PRODUCTIONIZATION. La demo `MundoPinturasDiana-Demo` queda intacta y el portal de produccion vive en `mpdw-frontend`.
- Classification: FULL_STACK
- Complexity: COMPLEX (92). Autenticacion, sesion, datos personales, migracion y correo.
- Routing: backend, frontend e integrador.

### Decisiones
- Los mensajes de las historias reemplazan los textos previos del servicio. Las pruebas unitarias quedaron alineadas.
- La columna fisica del refresh sigue llamandose `fecha_expiracion_absoluta`. El dominio expone `fecha_expiracion` para no reescribir el esquema que ya usa el resto del backend.
- El hash de contraseña sigue en la columna `password` de Django (Argon2id). No se duplica.
- Si el administrador debe cambiar la contraseña y ademas tiene 2FA, primero cambia la contraseña y despues verifica el codigo. Mientras tanto el JWT no abre el resto de la API.
- El enlace de recuperacion viaja en el fragmento `#rt=` para que el token no quede en los logs del servidor web. En base de datos solo se guarda el hash.
- El correo sale por SendGrid si hay API key y, si no, por el SMTP del entorno. El `.env` local no se versiona.

### Backend
- Migracion `0004_epic1_autenticacion`.
- Servicios, vistas, puerto de correo, adaptador SMTP y plantillas HTML.
- Pruebas: `tests/unit/test_auth_service.py`, `tests/unit/test_epic1_auth.py` y el contrato OpenAPI.

### Evidencia
- `uv run pytest tests/unit -m unit`: 152 passed.
- `uv run mypy apps/m01_identidad apps/m13_plataforma/adapters`: sin errores.
- `uv run ruff check` sobre los archivos tocados: sin errores.
- `uv run python scripts/scan_secrets.py`: sin hallazgos en archivos versionados.
- `uv run python scripts/complejidad.py`: todas las funciones de `services.py` bajo 20.
- Cobertura de la suite unitaria: 94.12% (umbral 90%).

### No verificado en esta corrida
- La suite de integracion con PostgreSQL no se ejecuto en esta maquina porque no habia un servicio local levantado. El pipeline de CI si la ejecuta.

## Epica 2 — Administracion de usuarios y perfil
**Status:** COMPLETED
**Date:** 2026-11-05

### Analysis (orchestrator)
- project_mode: EXTEND_EXISTING en `m01_identidad`; FULL_STACK con contrato OpenAPI unico.
- Orden de ejecucion: HU 07 (modelo y creacion) → HU 08 (listado) → HU 09–11 (detalle) → HU 12 (perfil propio reutiliza PATCH profile).

### Backend
- Migracion `0006_epic2_perfil_usuarios`; brecha B-18 resuelta con generacion aleatoria y correo `enviar_contrasena_inicial`.
- `AdminUsuariosService` con `transaction.atomic`, bloqueo optimista por `version_fila` y auditoria sin secretos.
- Vistas en `admin_views.py` montadas en `/api/v1/usuarios/`.

### Evidencia
- `make calidad`: 9 puertas en verde (cobertura unitaria >= 90%).
- Pruebas: `tests/unit/test_epic2_usuarios.py`, `tests/integration/test_epic2_usuarios_api.py`.

## Epica 3 — Roles, permisos y control de acceso
**Status:** COMPLETED  
**Date:** 2026-11-05  
**Branch:** `epica-3-roles-permisos`

### Backend
- Migracion `0008_epic3_roles_permisos` (campos HU 13–16, `Rol_permiso.permitido`).
- `AdminRolesPermisosService` + vistas bajo `/api/v1/roles-permisos/`; accesos de menu en `GET /api/v1/auth/accesos-panel`.
- Evaluacion RN-US-03 en `PermissionRepository` / `PermissionService.accesos_panel`.

### Evidencia
- `make calidad`: ruff, mypy, import-linter, bandit, OpenAPI, pytest unit (201 tests, cobertura ~90%).
- `tests/unit/test_epic3_roles_permisos.py`, `test_epic3_roles_views.py`, `tests/integration/test_epic3_roles_api.py`.

## Iteración 7 — Ajustes Épica 2 y 3
**Status:** COMPLETED  
**Date:** 2026-11-05  
**Branch:** `epica-3-ajustes-y-fixes`

- `permiso_eval`, `PermissionRepository`, `eliminar_rol`, OpenAPI `DELETE` rol.
- Cobertura unitaria 90.24% (210 tests).
- `docs/correcciones-iteracion-7.md`.

## Cierre Sprint 1 — Épicas 13 y 18 (v1.1.5)
**Status:** COMPLETED  
**Date:** 2026-11-06  
**Branch:** `epica-13-18-cierre-sprint1`

### Alcance
- **Épica 13 (HU 82):** API de solo lectura para bitácora con filtros, validación estricta de paginación y fechas, sanitización de secretos en persistencia de auditoría, permiso de consulta para gerente vía datos semilla.
- **Épica 18 (backend):** coherencia de `ConflictoVersionError` → HTTP 409; motivo obligatorio en operaciones críticas de usuario donde aplica; mensajes alineados con HU 96/97 en capa dominio.

### Evidencia
- `make calidad`: 9 puertas en verde; cobertura unitaria ≥90%.
- Pruebas: `tests/unit/test_epic13_bitacora_service.py`, `test_epic13_auditoria_sanitize.py`; ajustes en `test_epic2_usuarios.py`, `test_epic4_sedes.py`.
- OpenAPI: `docs/openapi.yaml` regenerado.

## Épica 5 — Catálogo de productos
**Status:** COMPLETED
**Date:** 2026-11-11

- Alta, listado filtrado, edición con historial de precio, estado, parámetros, importación CSV/XLSX y exportación.
- Pruebas: `tests/unit/test_epic5_catalogo.py`.
- Permisos de matriz: deja de ejecutar un `get_or_create` por celda en cada lectura.

## Épica 6 — Inventario y kardex
**Status:** COMPLETED
**Date:** 2026-11-11
**Branch:** `epica-6-inventario-kardex`

- Existencias, kardex, entrada, ajuste/merma y traslado en `AdminInventarioService`.
- Pruebas: `tests/unit/test_epic6_inventario.py`.
- Cobertura unitaria ≥ 90%.

## Épica 7 — Directorio de clientes y Habeas Data
**Status:** COMPLETED  
**Date:** 2026-11-12  
**Branch:** `epica-7-directorio-clientes-habeas-data`  
**Version:** v1.2.3

- CRUD clientes/tipos, e.164, consentimiento Habeas Data, WhatsApp, historial/métricas.
- Pruebas: `tests/unit/test_epic7_clientes.py`; OpenAPI regenerado.
- `make calidad` en verde; cobertura unitaria ≥ 90%.

## Épica 12 — Eventos y novedades
**Status:** COMPLETED  
**Date:** 2026-11-12  
**Branch:** `epicas-12-14-eventos-proveedores`  
**Version:** v1.2.4

- Modelo ampliado, admin API, endpoint público y sedes activas.
- Pruebas: `tests/unit/test_epic12_eventos.py`.

## Épica 14 — Proveedores e integración inventario
**Status:** COMPLETED  
**Date:** 2026-11-12  
**Branch:** `epicas-12-14-eventos-proveedores`  
**Version:** v1.2.5

- App `m14_proveedores`, FK en kardex, purga de datos de prueba de inventario.
- Pruebas: `tests/unit/test_epic14_proveedores.py`; suite unitaria 292 passed, cobertura ≥ 90%.
