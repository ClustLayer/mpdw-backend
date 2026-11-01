"""
WSGI config para proyecto MPDW.
SAD Ref: ADR-004, §13.2
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_wsgi_application()

