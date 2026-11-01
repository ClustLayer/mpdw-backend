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

# Base de datos de prueba (SQLite en memoria si no hay Postgres configurado)
if not os.environ.get("DATABASE_URL"):
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

