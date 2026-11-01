# ==============================================================================
# Manejador Uniforme de Excepciones - MPDW
# SAD Ref: §9.1, §10.5
# ==============================================================================
import logging
from typing import Any

from django.conf import settings
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response

from contratos.excepciones import (
    AutenticacionError,
    ConflictoVersionError,
    DominioError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    ReglaNegocioError,
    SedeNoAutorizadaError,
    StockInsuficienteError,
)

logger = logging.getLogger(__name__)


def uniform_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Transforma todas las excepciones en el cuerpo uniforme: {codigo, mensaje, detalles, idCorrelacion}."""
    request = context.get("request")
    correlation_id = getattr(request, "correlation_id", "sin-correlacion")

    codigo = "ERROR_INTERNO"
    mensaje = "Ocurrio un error interno en el servidor."
    detalles: list[Any] = []
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, ConflictoVersionError | StockInsuficienteError):
        codigo = exc.codigo
        mensaje = exc.mensaje
        detalles = exc.detalles
        status_code = status.HTTP_409_CONFLICT

    elif isinstance(exc, SedeNoAutorizadaError | PermisoDenegadoError | PermissionDenied):
        codigo = getattr(exc, "codigo", "ACCESO_DENEGADO")
        mensaje = str(exc) if isinstance(exc, DominioError) else "Permiso insuficiente."
        status_code = status.HTTP_403_FORBIDDEN

    elif isinstance(exc, AutenticacionError | AuthenticationFailed | NotAuthenticated):
        codigo = getattr(exc, "codigo", "NO_AUTENTICADO")
        mensaje = str(exc) if isinstance(exc, DominioError) else "Credenciales invalidas o expiradas."
        status_code = status.HTTP_401_UNAUTHORIZED

    elif isinstance(exc, RecursoNoEncontradoError | NotFound | Http404):
        codigo = getattr(exc, "codigo", "NO_ENCONTRADO")
        mensaje = str(exc) if isinstance(exc, DominioError) else "El recurso solicitado no existe."
        status_code = status.HTTP_404_NOT_FOUND

    elif isinstance(exc, ReglaNegocioError):
        codigo = exc.codigo
        mensaje = exc.mensaje
        detalles = exc.detalles
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    elif isinstance(exc, ValidationError):
        codigo = "DATOS_INVALIDOS"
        mensaje = "Los datos enviados no son validos."
        detalles = [exc.detail] if isinstance(exc.detail, dict | list) else [str(exc.detail)]
        status_code = status.HTTP_400_BAD_REQUEST

    elif isinstance(exc, Throttled):
        codigo = "LIMITE_TASA_EXCEDIDO"
        wait_seconds = getattr(exc, "wait", 60)
        mensaje = f"Limite de solicitudes excedido. Intente nuevamente en {wait_seconds} segundos."
        status_code = status.HTTP_429_TOO_MANY_REQUESTS

    elif isinstance(exc, DominioError):
        codigo = exc.codigo
        mensaje = exc.mensaje
        detalles = exc.detalles
        status_code = status.HTTP_400_BAD_REQUEST

    else:
        # Error no controlado: loggear traza interna con correlación y retornar respuesta limpia
        logger.exception("Error 500 no controlado [%s]: %s", correlation_id, exc)
        if settings.DEBUG:
            detalles = [str(exc)]

    cuerpo = {
        "codigo": codigo,
        "mensaje": mensaje,
        "detalles": detalles,
        "idCorrelacion": correlation_id,
    }
    return Response(cuerpo, status=status_code)

