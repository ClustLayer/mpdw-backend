from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m07_domicilios.admin_domicilios_service import AdminDomiciliosService
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError

PERM_VER = ("domicilios", "Consultar")
PERM_CREAR = ("domicilios", "Crear")
PERM_EDITAR = ("domicilios", "Editar")


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
    elif exc.codigo == "NO_ENCONTRADO":
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


class DomicilioBandejaView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="domicilios_bandeja")
    def get(self, request: Request) -> Response:
        try:
            data = AdminDomiciliosService().bandeja(
                request.query_params.get("estado"),
                _int_param(request, "id_mensajero") or None,
                request.query_params.get("fecha_desde"),
                request.query_params.get("fecha_hasta"),
                _int_param(request, "id_sede") or None,
                request.query_params.get("orden") or "desc",
                max(1, _int_param(request, "page", 1)),
                max(1, min(100, _int_param(request, "page_size", 20))),
                request.query_params.get("vista"),
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class DomicilioCreateView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CREAR

    @extend_schema(operation_id="domicilios_crear")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminDomiciliosService().crear(_ctx(request), body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class DomicilioPrecargaFacturaView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CREAR

    @extend_schema(operation_id="domicilios_precarga_factura")
    def get(self, request: Request, id_factura: int) -> Response:
        try:
            data = AdminDomiciliosService().precarga_factura(id_factura)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class DomicilioDetalleView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="domicilios_detalle")
    def get(self, request: Request, id_entrega: int) -> Response:
        try:
            data = AdminDomiciliosService().detalle(id_entrega)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class DomicilioAsignarView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR

    @extend_schema(operation_id="domicilios_asignar_mensajero")
    def post(self, request: Request, id_entrega: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminDomiciliosService().asignar_mensajero(_ctx(request), id_entrega, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class DomicilioEstadoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR

    @extend_schema(operation_id="domicilios_cambiar_estado")
    def post(self, request: Request, id_entrega: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminDomiciliosService().cambiar_estado(_ctx(request), id_entrega, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class MensajerosActivosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="mensajeros_activos")
    def get(self, request: Request) -> Response:
        return Response(AdminDomiciliosService().mensajeros_activos())


class MensajeroListCreateView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_CREAR if self.request.method == "POST" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="mensajeros_listar")
    def get(self, request: Request) -> Response:
        data = AdminDomiciliosService().mensajeros_listar(
            str(request.query_params.get("q") or ""),
            request.query_params.get("estado"),
            max(1, _int_param(request, "page", 1)),
            max(1, min(100, _int_param(request, "page_size", 20))),
        )
        return Response(data)

    @extend_schema(operation_id="mensajeros_crear")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminDomiciliosService().mensajero_crear(_ctx(request), body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class MensajeroDetailView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR

    @extend_schema(operation_id="mensajeros_actualizar")
    def patch(self, request: Request, id_mensajero: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminDomiciliosService().mensajero_actualizar(_ctx(request), id_mensajero, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class HistorialMensajeriaView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="domicilios_historial")
    def get(self, request: Request) -> Response:
        try:
            data = AdminDomiciliosService().historial(
                _int_param(request, "id_mensajero") or None,
                _int_param(request, "id_cliente") or None,
                request.query_params.get("fecha_desde"),
                request.query_params.get("fecha_hasta"),
                request.query_params.get("estado"),
                max(1, _int_param(request, "page", 1)),
                max(1, min(100, _int_param(request, "page_size", 20))),
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)
