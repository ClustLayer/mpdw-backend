from typing import Any, cast

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m06_ventas.admin_facturacion_externa_service import AdminFacturacionExternaService
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError

PERM_VER = ("facturacion_electronica", "Consultar")
PERM_EDITAR = ("facturacion_electronica", "Editar")


def _ctx(request: Request) -> AuthContext:
    ctx = getattr(request, "auth_context", None)
    if not isinstance(ctx, AuthContext):
        raise ReglaNegocioError("Contexto de autenticacion ausente.", codigo="NO_AUTORIZADO")
    return ctx


def _err(exc: ReglaNegocioError, request: Request) -> Response:
    code: int = status.HTTP_400_BAD_REQUEST
    if exc.codigo == "NO_AUTORIZADO":
        code = status.HTTP_403_FORBIDDEN
    elif exc.codigo == "CONCURRENCIA":
        code = status.HTTP_409_CONFLICT
    elif exc.codigo in ("NO_ENCONTRADO", "SIN_SOPORTE", "ESTADO_INVALIDO"):
        code = status.HTTP_404_NOT_FOUND
    return Response(
        {
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": exc.detalles,
            "idCorrelacion": getattr(request, "correlation_id", ""),
        },
        status=code,
    )


def _int_param(request: Request, key: str, default: int = 0) -> int:
    raw = request.query_params.get(key)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class FacturacionExternaBandejaView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="facturacion_externa_bandeja")
    def get(self, request: Request) -> Response:
        try:
            data = AdminFacturacionExternaService().bandeja(
                request.query_params.get("estado"),
                request.query_params.get("fecha_desde"),
                request.query_params.get("fecha_hasta"),
                request.query_params.get("numero"),
                max(1, _int_param(request, "page", 1)),
                max(1, min(100, _int_param(request, "page_size", 20))),
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class FacturacionExternaDetalleView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="facturacion_externa_detalle")
    def get(self, request: Request, pk: int) -> Response:
        try:
            data = AdminFacturacionExternaService().detalle(pk)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class FacturacionExternaSoporteView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="facturacion_externa_soporte")
    def get(self, request: Request, pk: int) -> Response:
        try:
            data = AdminFacturacionExternaService().url_soporte(pk)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class FacturacionExternaEstadoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR

    @extend_schema(operation_id="facturacion_externa_estado")
    def post(self, request: Request, pk: int) -> Response:
        try:
            body = cast(dict[str, Any], request.data)
            data = AdminFacturacionExternaService().actualizar_estado(_ctx(request), pk, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)
