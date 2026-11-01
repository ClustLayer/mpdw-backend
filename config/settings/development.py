# ==============================================================================
# Configuración de Desarrollo Local - MPDW
# SAD Ref: §13.1, §13.4
# ==============================================================================
from config.settings.base import *  # noqa: F403

DEBUG = True

# Permitir orígenes locales para desarrollo de frontend
CORS_ALLOW_ALL_ORIGINS = True

# Desactivar HTTPS estricto en local
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

