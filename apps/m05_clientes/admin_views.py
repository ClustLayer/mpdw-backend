from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m05_clientes.admin_clientes_service import AdminClientesService
from apps.m05_clientes.models import Clientes
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError

PERM_VER = ("clientes", "Consultar")
PERM_CREAR = ("clientes", "Crear")
PERM_EDITAR = ("clientes", "Editar")


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
    payload: dict = {
        "codigo": exc.codigo,
        "mensaje": exc.mensaje,
        "detalles": exc.detalles,
        "idCorrelacion": getattr(request, "correlation_id", ""),
    }
    if exc.codigo == "TELEFONO_DUPLICADO" and exc.detalles:
        payload["coincidencia"] = exc.detalles[0]
    return Response(payload, status=code)


class ClienteAdminListCreateView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_CREAR if self.request.method == "POST" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="clientes_listar")
    def get(self, request: Request) -> Response:
        q = str(request.query_params.get("q") or "")
        id_tipo = request.query_params.get("id_tipo_cliente")
        estado = str(request.query_params.get("estado") or "todos")
        page = int(request.query_params.get("page") or 1)
        page_size = min(100, int(request.query_params.get("page_size") or 20))
        try:
            data = AdminClientesService().listar(q, int(id_tipo) if id_tipo else None, estado, page, page_size)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)

    @extend_schema(operation_id="clientes_crear")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminClientesService().crear(_ctx(request), body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class ClienteAdminDetailView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_EDITAR if self.request.method == "PATCH" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="clientes_detalle")
    def get(self, request: Request, pk: int) -> Response:
        try:
            data = AdminClientesService().obtener(pk)
        except Clientes.DoesNotExist:
            return Response({"mensaje": "Cliente no encontrado."}, status=404)
        return Response(data)

    @extend_schema(operation_id="clientes_actualizar")
    def patch(self, request: Request, pk: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminClientesService().actualizar(_ctx(request), pk, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class ClienteTelefonoCheckView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="clientes_verificar_telefono")
    def get(self, request: Request) -> Response:
        telefono = str(request.query_params.get("numero_telefono") or "")
        excluir = request.query_params.get("id_cliente")
        try:
            dup = AdminClientesService().verificar_telefono(telefono, int(excluir) if excluir else None)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(dup or {"mensaje": "OK"})


class TipoClienteAdminView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_CREAR if self.request.method == "POST" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="tipos_cliente_listar")
    def get(self, request: Request) -> Response:
        solo = str(request.query_params.get("solo_activos") or "").lower() in ("1", "true", "si")
        return Response(AdminClientesService().tipos_listado(solo_activos=solo))

    @extend_schema(operation_id="tipos_cliente_crear")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminClientesService().crear_tipo(_ctx(request), body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class TipoClienteDetalleView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR

    @extend_schema(operation_id="tipos_cliente_actualizar")
    def patch(self, request: Request, pk: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminClientesService().actualizar_tipo(_ctx(request), pk, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class ClienteHistorialView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="clientes_historial")
    def get(self, request: Request, pk: int) -> Response:
        desde = str(request.query_params.get("desde") or "") or None
        hasta = str(request.query_params.get("hasta") or "") or None
        page = int(request.query_params.get("page") or 1)
        page_size = min(50, int(request.query_params.get("page_size") or 10))
        incluir = str(request.query_params.get("metricas") or "1").lower() not in ("0", "false", "no")
        try:
            data = AdminClientesService().historial(_ctx(request), pk, desde, hasta, page, page_size, incluir)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)
