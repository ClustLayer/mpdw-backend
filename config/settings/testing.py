# ==============================================================================
# Configuración de Pruebas (pytest) - MPDW
# SAD Ref: §14.1, §14.2, Regla R3
# ==============================================================================
import os

from config.settings.base import *  # noqa: F403

DEBUG = False

# Hasher rápido para acelerar la suite de pruebas
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Las pruebas locales nunca deben usar la base en nube del .env de desarrollo.
# CI/GitHub Actions define MPDW_TEST_USE_POSTGRES=true y DATABASE_URL efímera.
_use_postgres = os.environ.get("MPDW_TEST_USE_POSTGRES", "").lower() in {
    "1",
    "true",
    "yes",
} or os.environ.get("GITHUB_ACTIONS") == "true"

if not _use_postgres:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
        "direct": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
        "bi": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
    }

# Desactivar throttling en pruebas automáticas
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

# Caché en memoria: evita depender de django_cache cuando se usa SQLite :memory:
CACHES = {  # noqa: F405
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mpdw-tests",
    }
}
