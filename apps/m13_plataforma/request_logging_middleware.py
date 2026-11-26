"""Middleware opcional: envía metadatos de petición a logs generales."""

from __future__ import annotations

import time
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from apps.m13_plataforma.observability.general_log_writer import get_general_log_writer


class RequestLoggingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self._enabled = bool(getattr(settings, "REQUEST_LOGGING_ENABLED", False))

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self._enabled:
            return self.get_response(request)
        t0 = time.perf_counter()
        response = self.get_response(request)
        ms = (time.perf_counter() - t0) * 1000.0
        cid = getattr(request, "correlation_id", "")
        try:
            get_general_log_writer().log_http(
                metodo=request.method or "GET",
                ruta=request.path[:500],
                status=response.status_code,
                correlation_id=str(cid),
                ms=ms,
            )
        except Exception:  # pragma: no cover
            pass
        return response
