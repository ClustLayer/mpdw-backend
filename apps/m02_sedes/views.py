from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m01_identidad.serializers import MensajeResponseSerializer
from apps.m02_sedes.admin_sedes_service import AdminSedesService
from apps.m02_sedes.serializers import (
    ConsolidadoQuerySerializer,
    CrearSedeRequestSerializer,
    EditarSedeRequestSerializer,
    SedePublicSerializer,
)
from contratos.dtos import AuthContext
from contratos.excepciones import DominioError, ReglaNegocioError

PERM_SEDES = ("sedes", "T")


def _ctx(request: Request) -> AuthContext:
    ctx: AuthContext | None = getattr(request, "auth_context", None)
    if ctx is None:
        raise ReglaNegocioError("Contexto de autenticacion ausente.", codigo="NO_AUTORIZADO")
    return ctx


def _err(exc: ReglaNegocioError | DominioError, request: Request) -> Response:
    code: int = status.HTTP_400_BAD_REQUEST
    if exc.codigo == "NO_AUTORIZADO":
        code = status.HTTP_403_FORBIDDEN
    elif exc.codigo == "CONCURRENCIA":
        code = status.HTTP_409_CONFLICT
    cid = getattr(request, "correlation_id", "")
    codigo_resp = exc.codigo
    if codigo_resp == "CONCURRENCIA":
        codigo_resp = "CONFLICTO_CONCURRENCIA"
    return Response(
        {"codigo": codigo_resp, "mensaje": exc.mensaje, "detalles": [], "idCorrelacion": cid},
        status=code,
    )


class SedePublicListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: SedePublicSerializer(many=True)})
    def get(self, request: Request) -> Response:
        data = AdminSedesService().listar_publicas()
        return Response(data)


class SedeListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_SEDES

    @extend_schema(responses={200: SedePublicSerializer(many=True)})
    def get(self, request: Request) -> Response:
        params = request.query_params
        try:
            page = max(1, int(params.get("page") or 1))
            page_size = min(100, max(1, int(params.get("page_size") or 20)))
        except (TypeError, ValueError):
            return Response(
                {"codigo": "PAGINACION_INVALIDA", "mensaje": "Paginación inválida."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        body = AdminSedesService().listar(
            q=params.get("q") or "",
            estado=params.get("estado") or "todos",
            page=page,
            page_size=page_size,
        )
        return Response(body)

    @extend_schema(request=CrearSedeRequestSerializer, responses={201: MensajeResponseSerializer})
    def post(self, request: Request) -> Response:
        ser = CrearSedeRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            detalle, msg = AdminSedesService().crear(_ctx(request), ser.validated_data)
            return Response({**detalle, "mensaje": msg}, status=status.HTTP_201_CREATED)
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class SedeDetailView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_SEDES

    @extend_schema(request=EditarSedeRequestSerializer, responses={200: MensajeResponseSerializer})
    def patch(self, request: Request, id_sede: int) -> Response:
        ser = EditarSedeRequestSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            detalle, msg = AdminSedesService().editar(_ctx(request), id_sede, ser.validated_data)
            return Response({**detalle, "mensaje": msg})
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class SedeConsolidadoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("sedes", "T")

    @extend_schema(responses={200: MensajeResponseSerializer})
    def get(self, request: Request) -> Response:
        ser = ConsolidadoQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        try:
            data = AdminSedesService().consolidado(
                _ctx(request),
                v.get("id_sede"),
                v["fecha_inicio"],
                v["fecha_fin"],
            )
            return Response(data)
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


