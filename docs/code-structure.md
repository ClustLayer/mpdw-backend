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

### Services
- AuthService, RecuperacionService, ContrasenaService, Verificacion2FAService (`apps/m01_identidad/services.py`)
- SmtpEmailAdapter y SendGridEmailAdapter (`apps/m13_plataforma/adapters`)

### Models
- Usuarios: `debe_cambiar_password`, `ultimo_acceso`, `fecha_actualizacion`, email de 255. El hash vive en la columna `password` de Django y se expone como `password_hash`.
- Sesiones_usuario: `fecha_revocacion`, `mfa_verificada`. `fecha_expiracion` es el alias de `fecha_expiracion_absoluta`.
- Tokens_recuperacion y Codigos_2fa: `fecha_creacion`. Solo se persiste el hash.

## Critical structures
- `apps/m01_identidad/authentication.py` — rechaza el desafio 2FA como access token y bloquea el resto de rutas si falta el cambio de contraseña o el segundo factor.
- `docs/openapi.yaml` — contrato publicado. Se regenera con `manage.py spectacular`.
- `.env` — fuera de Git. El pipeline ejecuta `scripts/scan_secrets.py` sobre los archivos versionados.
