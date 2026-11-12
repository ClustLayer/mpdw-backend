# ==============================================================================
# Configuración de Producción (Render) - MPDW
# SAD Ref: ADR-012, §13.4, Regla R6
# ==============================================================================
import os

from config.settings.base import *  # noqa: F403

DEBUG = False

# Validación fail-fast de secretos obligatorios
required_secrets = ["DJANGO_SECRET_KEY", "JWT_SIGNING_KEY", "DATABASE_URL"]
missing_secrets = [s for s in required_secrets if not os.environ.get(s)]
if missing_secrets:
    raise RuntimeError(f"Faltan variables de entorno requeridas en produccion: {', '.join(missing_secrets)}")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# Validación de seguridad para contraseña de administrador inicial si se define
initial_admin_pwd = os.environ.get("INITIAL_ADMIN_PASSWORD", "")
if initial_admin_pwd:
    if "PLACEHOLDER" in initial_admin_pwd or len(initial_admin_pwd) < 10 or not any(c.isupper() for c in initial_admin_pwd) or not any(c.isdigit() for c in initial_admin_pwd):
        raise RuntimeError(
            "INITIAL_ADMIN_PASSWORD en produccion no cumple la politica de seguridad "
            "(minimo 10 caracteres, una mayuscula, un numero y sin placeholders)."
        )

# Seguridad HTTP estricta
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CORS Estricto hacia los orígenes de Vercel
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "https://mundopinturasdiana.com,https://www.mundopinturasdiana.com",
    ).split(",")
    if origin.strip()
]

# Pooler Supabase: SSL + sin cursores server-side (ADR-003)
for _db in DATABASES.values():  # noqa: F405
    if not isinstance(_db, dict):
        continue
    _db["DISABLE_SERVER_SIDE_CURSORS"] = True
    _db["CONN_MAX_AGE"] = 0
    _opts_raw = _db.get("OPTIONS")
    _opts: dict[str, object] = dict(_opts_raw) if isinstance(_opts_raw, dict) else {}
    _opts["prepare_threshold"] = None
    if "sslmode" not in _opts:
        _opts["sslmode"] = "require"
    _db["OPTIONS"] = _opts

