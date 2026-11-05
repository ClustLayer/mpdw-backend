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

### Services
- AuthService, RecuperacionService, ContrasenaService, Verificacion2FAService (`apps/m01_identidad/services.py`)
- AdminUsuariosService, PerfilPropioService (`apps/m01_identidad/admin_usuarios_service.py`)
- SmtpEmailAdapter y SendGridEmailAdapter (`apps/m13_plataforma/adapters`)

### Models
- Usuarios: `apellido`, `telefono`, `debe_cambiar_password`, `ultimo_acceso`, `version_fila`, `contrasena_temporal_expira`, email de 255. El hash vive en la columna `password` de Django y se expone como `password_hash`.
- Sesiones_usuario: `fecha_revocacion`, `mfa_verificada`. `fecha_expiracion` es el alias de `fecha_expiracion_absoluta`.
- Tokens_recuperacion y Codigos_2fa: `fecha_creacion`. Solo se persiste el hash.

## Critical structures
- `apps/m01_identidad/authentication.py` — rechaza el desafio 2FA como access token y bloquea el resto de rutas si falta el cambio de contraseña o el segundo factor.
- `docs/openapi.yaml` — contrato publicado. Se regenera con `manage.py spectacular`.
- `.env` — fuera de Git. El pipeline ejecuta `scripts/scan_secrets.py` sobre los archivos versionados.
