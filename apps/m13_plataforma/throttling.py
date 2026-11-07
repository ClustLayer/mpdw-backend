# ==============================================================================
# Límite de Tasa con Caché de Base de Datos - MPDW
# SAD Ref: ADR-010, I-01
# ==============================================================================
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import caches
from django.db import DatabaseError, OperationalError
from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)


class DatabaseCacheRateThrottle(SimpleRateThrottle):
    """Throttle que almacena contadores en la tabla django_cache de PostgreSQL.

    Si la caché/BD no está disponible (p. ej. fallo transitorio del pooler),
    degrada de forma segura permitiendo la petición en lugar de devolver 500.
    """

    cache = caches["default"]
    scope = "anon"

    def get_rate(self) -> str:
        rates: dict[str, str] = getattr(settings, "REST_FRAMEWORK", {}).get(
            "DEFAULT_THROTTLE_RATES", {}
        )
        return rates.get(self.scope, "60/min")

    def allow_request(self, request: Request, view: Any) -> bool:
        if request.user and getattr(request.user, "is_authenticated", False):
            self.scope = "user"
        else:
            self.scope = "anon"
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        try:
            return super().allow_request(request, view)
        except (OperationalError, DatabaseError) as exc:
            logger.warning(
                "Throttle degradado: caché/BD no disponible (%s).",
                exc.__class__.__name__,
            )
            return True

    def get_cache_key(self, request: Request, view: Any) -> str | None:
        if request.user and getattr(request.user, "is_authenticated", False):
            ident: Any = request.user.pk
            scope = "user"
        else:
            ident = self.get_ident(request)
            scope = "anon"
        return self.cache_format % {"scope": scope, "ident": ident}
