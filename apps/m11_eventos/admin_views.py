from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m11_eventos.admin_eventos_service import AdminEventosService
from apps.m11_eventos.models import Eventos_novedades
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError

PERM_VER = ("eventos", "Consultar")
PERM_CREAR = ("eventos", "Crear")
PERM_EDITAR = ("eventos", "Editar")


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
    return Response(
        {
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": exc.detalles,
            "idCorrelacion": getattr(request, "correlation_id", ""),
        },
        status=code,
    )


class EventosPublicosView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(operation_id="eventos_publicos")
    def get(self, request: Request) -> Response:
        return Response(AdminEventosService().publicos())


class SedesActivasEventosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="eventos_sedes_activas")
    def get(self, request: Request) -> Response:
        return Response(AdminEventosService().sedes_activas())


class EventoAdminListCreateView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_CREAR if self.request.method == "POST" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="eventos_listar")
    def get(self, request: Request) -> Response:
        q = str(request.query_params.get("q") or "")
        estado = str(request.query_params.get("estado") or "todos")
        page = int(request.query_params.get("page") or 1)
        page_size = min(100, int(request.query_params.get("page_size") or 20))
        try:
            data = AdminEventosService().listar(q, estado, page, page_size)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)

    @extend_schema(operation_id="eventos_crear")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminEventosService().crear(_ctx(request), body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class EventoAdminDetailView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_EDITAR if self.request.method == "PATCH" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="eventos_detalle")
    def get(self, request: Request, pk: int) -> Response:
        try:
            data = AdminEventosService().obtener(pk)
        except Eventos_novedades.DoesNotExist:
            return Response({"mensaje": "Evento no encontrado."}, status=404)
        return Response(data)

    @extend_schema(operation_id="eventos_actualizar")
    def patch(self, request: Request, pk: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminEventosService().actualizar(_ctx(request), pk, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)
