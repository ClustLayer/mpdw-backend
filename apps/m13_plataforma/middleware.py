# ==============================================================================
# Middlewares de Plataforma: Correlación y CORS/Cabeceras - MPDW
# SAD Ref: TB-2, T-12, AD-11, §9.1, §10.9
# ==============================================================================
import uuid
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse


class CorrelationIdMiddleware:
    """Asegura que cada petición HTTP tenga un UUID de correlación trazable."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.correlation_id = correlation_id  # type: ignore[attr-defined]

        response = self.get_response(request)
        response["X-Correlation-ID"] = correlation_id
        return response


class CorsAndSecurityHeadersMiddleware:
    """Implementa CORS con lista blanca de orígenes y cabeceras de seguridad (SAD TB-2, T-12)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self._allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        self._allow_all = bool(getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False))

    def __call__(self, request: HttpRequest) -> HttpResponse:
        origin = request.headers.get("Origin")

        # Manejar preflight OPTIONS antes de que llegue a DRF
        if request.method == "OPTIONS" and origin:
            response = HttpResponse(status=200)
            if self._origen_permitido(origin):
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Credentials"] = "true"
                response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                response["Access-Control-Allow-Headers"] = (
                    "Authorization, Content-Type, If-Match, Idempotency-Key, X-Correlation-ID"
                )
                response["Access-Control-Max-Age"] = "86400"
            return response

        response = self.get_response(request)

        # Aplicar CORS si el origen está en lista blanca
        if origin and self._origen_permitido(origin):
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Expose-Headers"] = "ETag, X-Correlation-ID"

        # Cabeceras de seguridad OWASP
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        return response

    def _origen_permitido(self, origin: str) -> bool:
        return self._allow_all or origin in self._allowed_origins or "*" in self._allowed_origins
