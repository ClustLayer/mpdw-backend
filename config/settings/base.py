# ==============================================================================
# Configuración Base de Django - MPDW
# SAD Ref: ADR-001, ADR-003, ADR-004, ADR-006, ADR-007, ADR-008, §13.4
# ==============================================================================
import logging
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    _settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    if _settings_module.endswith("testing"):
        load_dotenv(BASE_DIR / ".env.test", override=True)
    else:
        load_dotenv(BASE_DIR / ".env", override=False)
except ImportError:  # pragma: no cover
    _settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")

if not os.environ.get("DATABASE_URL") and os.environ.get("database_url"):
    os.environ["DATABASE_URL"] = os.environ["database_url"]

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-in-production-only-for-local-testing",
)

DEBUG = False

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,api.mundopinturasdiana.com,api.staging.mundopinturasdiana.com",
    ).split(",")
    if h.strip()
]

# ------------------------------------------------------------------------------
# Aplicaciones Instaladas (SAD §6.4, §6.6, C-13)
# Nota: django.contrib.admin NO se instala (SAD ADR-004)
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Extensiones de terceros
    "rest_framework",
    "drf_spectacular",
    # Módulos de dominio MPDW (M01-M13)
    "apps.m01_identidad.apps.M01IdentidadConfig",
    "apps.m02_sedes.apps.M02SedesConfig",
    "apps.m03_catalogo.apps.M03CatalogoConfig",
    "apps.m04_inventario.apps.M04InventarioConfig",
    "apps.m05_clientes.apps.M05ClientesConfig",
    "apps.m06_ventas.apps.M06VentasConfig",
    "apps.m07_domicilios.apps.M07DomiciliosConfig",
    "apps.m08_caja.apps.M08CajaConfig",
    "apps.m09_analitica.apps.M09AnaliticaConfig",
    "apps.m10_auditoria.apps.M10AuditoriaConfig",
    "apps.m11_eventos.apps.M11EventosConfig",
    "apps.m12_tienda_publica.apps.M12TiendaPublicaConfig",
    "apps.m14_proveedores.apps.M14ProveedoresConfig",
    "apps.m13_plataforma.apps.M13PlataformaConfig",
    # Proceso ETL
    "etl.apps.EtlConfig",
]

MIDDLEWARE = [
    "apps.m13_plataforma.middleware.CorrelationIdMiddleware",
    "apps.m13_plataforma.middleware.CorsAndSecurityHeadersMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ------------------------------------------------------------------------------
# Conexiones a Base de Datos (SAD ADR-003, ADR-013, §8.3)
# ------------------------------------------------------------------------------
def _ssl_required() -> bool:
    """SSL obligatorio fuera de desarrollo/pruebas locales."""
    module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    if module.endswith("production"):
        return True
    if module.endswith(("development", "testing")):
        return False
    flag = os.environ.get("DATABASE_SSL_REQUIRE", "").lower()
    return flag in {"1", "true", "yes"}


def parse_db_url(url_string: str, *, ssl_require: bool | None = None) -> dict[str, object]:
    """Parsea DATABASE_URL preservando usuario tenant (`postgres.PROJECT_REF`)."""
    if not url_string:
        return {}
    require_ssl = _ssl_required() if ssl_require is None else ssl_require
    cfg: dict[str, object] = dict(
        dj_database_url.parse(
            url_string,
            conn_max_age=0,
            ssl_require=require_ssl,
        )
    )
    # Conservar el usuario completo del pooler (no truncar en el punto).
    parsed = urlparse(url_string)
    if parsed.username:
        cfg["USER"] = unquote(parsed.username)
    if parsed.password is not None:
        # urlparse ya decodifica %XX una vez; no re-codificar para psycopg.
        cfg["PASSWORD"] = unquote(parsed.password)
    if cfg.get("PORT") is not None:
        cfg["PORT"] = str(cfg["PORT"])
    cfg["DISABLE_SERVER_SIDE_CURSORS"] = True
    options_raw = cfg.get("OPTIONS")
    options: dict[str, object] = dict(options_raw) if isinstance(options_raw, dict) else {}
    options["prepare_threshold"] = None
    cfg["OPTIONS"] = options
    user = str(cfg.get("USER") or "")
    host = str(cfg.get("HOST") or "")
    if "pooler.supabase.com" in host and user == "postgres":
        _logger.warning(
            "DATABASE_URL usa usuario 'postgres' en pooler Supabase; "
            "se espera 'postgres.<PROJECT_REF>' para autenticación."
        )
    return cfg


default_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://mpdw_app:app_secret_123@localhost:5432/mpdw_db",
)
direct_db_url = os.environ.get(
    "DATABASE_MIGRATE_URL",
    "postgresql://mpdw_migrate:migrate_secret_123@localhost:5432/mpdw_db",
)
bi_db_url = os.environ.get(
    "DATABASE_BI_URL",
    "postgresql://mpdw_bi:bi_secret_123@localhost:5432/mpdw_db",
)

DATABASES = {
    # Conexión por defecto: API -> pooler de Supabase en transaction mode (ADR-003)
    "default": parse_db_url(default_db_url),
    # Conexión directa / sesión para migraciones y ETL
    "direct": parse_db_url(direct_db_url),
    # Conexión de solo lectura para analítica
    "bi": parse_db_url(bi_db_url),
}

ATOMIC_REQUESTS = False

# ------------------------------------------------------------------------------
# Modelo de Usuario y Password Hasher (SAD ADR-004, ADR-006, §10.3)
# ------------------------------------------------------------------------------
AUTH_USER_MODEL = "m01_identidad.Usuarios"

PASSWORD_HASHERS = [
    "apps.m01_identidad.hashers.Argon2idPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
]

# ------------------------------------------------------------------------------
# Caché de Base de Datos para Throttles (SAD ADR-010, I-01)
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# ------------------------------------------------------------------------------
# Django REST Framework (SAD §9.1, §10.5)
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.m01_identidad.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.m13_plataforma.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.m13_plataforma.excepciones.uniform_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.m13_plataforma.throttling.DatabaseCacheRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "300/min",
        "auth": "5/min",
    },
    "UNAUTHENTICATED_USER": None,
}

# ------------------------------------------------------------------------------
# drf-spectacular (OpenAPI 3.0)
# ------------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Mundo Pinturas Diana Web (MPDW) API",
    "DESCRIPTION": "API REST transaccional para la gestión comercial y multi-sede de MPDW",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
}

# ------------------------------------------------------------------------------
# Internacionalización y Zona Horaria (SAD S-01, §8.5)
# ------------------------------------------------------------------------------
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Parámetros de Tokens JWT
JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY", "dev-jwt-signing-secret-key-at-least-32-chars")
JWT_KEY_ID = os.environ.get("JWT_KEY_ID", "k1")
ACCESS_TOKEN_LIFETIME_MINUTES = int(os.environ.get("ACCESS_TOKEN_LIFETIME_MINUTES", "15"))
REFRESH_TOKEN_LIFETIME_DAYS = int(os.environ.get("REFRESH_TOKEN_LIFETIME_DAYS", "7"))
INACTIVITY_TIMEOUT_MINUTES = int(os.environ.get("INACTIVITY_TIMEOUT_MINUTES", "60"))
SESSION_WARNING_MINUTES = int(os.environ.get("SESSION_WARNING_MINUTES", "5"))
MAX_INTENTOS_FALLIDOS = int(os.environ.get("MAX_INTENTOS_FALLIDOS", "5"))
BLOQUEO_MINUTOS = int(os.environ.get("BLOQUEO_MINUTOS", "15"))
RECUPERACION_MINUTOS = int(os.environ.get("RECUPERACION_MINUTOS", "60"))
CODIGO_2FA_MINUTOS = int(os.environ.get("CODIGO_2FA_MINUTOS", "10"))
MAX_INTENTOS_2FA = int(os.environ.get("MAX_INTENTOS_2FA", "3"))
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN", "localhost")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@mundopinturasdiana.com")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", DEFAULT_FROM_EMAIL)
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Mundo Pinturas Diana")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}

# Orígenes CORS permitidos (SAD TB-2, T-12, AD-11)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,https://mundopinturasdiana.com",
    ).split(",")
    if origin.strip()
]

