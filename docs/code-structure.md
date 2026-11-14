# Code structure

## Backend

### API endpoints
- POST /api/v1/auth/login (HU_MPDW_01_01) — credenciales, cookie HttpOnly de refresh y access token en el cuerpo
- POST /api/v1/auth/refresh (HU_MPDW_01_05) — rotacion del refresh token
- POST /api/v1/auth/logout (HU_MPDW_01_02) — revocacion de la familia
- POST /api/v1/auth/recuperar y POST /api/v1/auth/restablecer (HU_MPDW_01_03)
- POST /api/v1/auth/cambiar-contrasena (HU_MPDW_01_04)
- POST /api/v1/auth/verificar-2fa y POST /api/v1/auth/reenviar-2fa (HU_MPDW_01_06)
- GET /api/v1/auth/politica-sesion — minutos de inactividad y de aviso
- GET /api/v1/auth/contrato — mapa de rutas y mensajes para el frontend
- GET/PATCH /api/v1/auth/profile (HU_MPDW_01_12) — consulta y edicion del perfil propio
- GET /api/v1/usuarios/ (HU_MPDW_01_08) — listado con q, id_rol, estado, page
- POST /api/v1/usuarios/ (HU_MPDW_01_07) — creacion administrada
- GET/PATCH /api/v1/usuarios/{id}/ (HU_MPDW_01_09) — detalle y edicion
- POST /api/v1/usuarios/{id}/estado (HU_MPDW_01_10) — activar, desactivar, bloquear
- POST /api/v1/usuarios/{id}/contrasena-temporal (HU_MPDW_01_11)
- GET /api/v1/usuarios/roles — catalogo de roles activos
- GET /api/v1/auditoria/bitacora/ — HU_MPDW_01_82: listado paginado de auditoría (solo lectura; filtros `page`, `page_size`, `id_usuario`, `accion`, `entidad`, `id_entidad`, `fecha_desde`, `fecha_hasta`)
- GET /api/v1/auditoria/bitacora/usuarios/ — opciones para filtro de usuario (`q`, `limit`)

### Services
- AuthService, RecuperacionService, ContrasenaService, Verificacion2FAService (`apps/m01_identidad/services.py`)
- AdminUsuariosService, PerfilPropioService (`apps/m01_identidad/admin_usuarios_service.py`)
- AdminRolesPermisosService, panel_accesos (`admin_roles_permisos_service.py`, `panel_accesos.py`); rutas `urls_roles_permisos.py`
- SmtpEmailAdapter y SendGridEmailAdapter (`apps/m13_plataforma/adapters`)
- `BitacoraAuditoriaService` (`apps/m10_auditoria/bitacora_service.py`) — consulta de bitácora; `sanitize_auditoria_payload` (`sanitize.py`) — enmascaramiento antes de persistir en auditoría

### Models
- Usuarios: `apellido`, `telefono`, `debe_cambiar_password`, `ultimo_acceso`, `version_fila`, `contrasena_temporal_expira`, email de 255. El hash vive en la columna `password` de Django y se expone como `password_hash`.
- Sesiones_usuario: `fecha_revocacion`, `mfa_verificada`. `fecha_expiracion` es el alias de `fecha_expiracion_absoluta`.
- Tokens_recuperacion y Codigos_2fa: `fecha_creacion`. Solo se persiste el hash.

## Critical structures
- `apps/m01_identidad/authentication.py` — rechaza el desafio 2FA como access token y bloquea el resto de rutas si falta el cambio de contraseña o el segundo factor.
- `docs/openapi.yaml` — contrato publicado. Se regenera con `manage.py spectacular`.
- `apps/m10_auditoria/` — repositorio de auditoría append-only; vistas de bitácora bajo `urls.py` y `config/urls.py` (`api/v1/auditoria/`).
- `.env` — fuera de Git. El pipeline ejecuta `scripts/scan_secrets.py` sobre los archivos versionados.

## Épica 5 — Catálogo
- `apps/m03_catalogo/admin_catalogo_service.py`, `admin_views.py`, `urls_admin.py` — `/api/v1/catalogo/`.
- Migración `0002_epic5_catalogo_backoffice` (precios, imagen, parámetros, tipos base).
- RBAC: mapas de permiso en una pasada (`PermissionRepository._mapas`) y alta masiva de la matriz.

## Épica 6 — Inventario y kardex
- `apps/m04_inventario/admin_service.py`, `admin_views.py`, `urls_admin.py` — `/api/v1/inventario/`.
- Migración `0002_epic6_kardex_campos` (`referencia`, `proveedor_nombre`).
- El listado público sigue en `GET /api/v1/inventory/`.

## Épica 7 — Clientes y Habeas Data
- `apps/m05_clientes/admin_clientes_service.py`, `admin_views.py`, `urls_admin.py` — `/api/v1/clientes/`.
- Migración `0002_epic7_clientes` (campos HU 37–41 + índices + semilla «Común»).
- `apps/m06_ventas/migrations/0002_detalle_factura.py` — líneas para métricas HU 42.

## Épica 14 — Proveedores
- `apps/m14_proveedores/admin_proveedores_service.py`, `admin_views.py`, `urls_admin.py` — `/api/v1/proveedores/`.
- Inventario: FK `id_proveedor` en `Movimientos_inventario` (`0004_epic14_proveedor_fk`).

## Épica 12 — Eventos y novedades
- `apps/m11_eventos/admin_eventos_service.py`, `admin_views.py`, `urls_admin.py` — `/api/v1/eventos/`.
- Migración `0002_epic12_eventos`.
