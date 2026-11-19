from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m06_ventas.admin_ventas_service import AdminVentasService
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError

PERM_POS_VER = ("pos", "Consultar")
PERM_POS_CREAR = ("pos", "Crear")
PERM_FACTURAS_VER = ("facturas", "Consultar")
PERM_FACTURAS_TOTAL = ("facturas", "Total")


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


class PosCatalogosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_POS_VER

    @extend_schema(operation_id="pos_catalogos")
    def get(self, request: Request) -> Response:
        return Response(AdminVentasService().catalogos_pos())


class PosBuscarProductosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_POS_VER

    @extend_schema(operation_id="pos_buscar_productos")
    def get(self, request: Request) -> Response:
        q = str(request.query_params.get("q") or "")
        id_sede = int(request.query_params.get("id_sede") or 0)
        if not id_sede:
            return Response({"mensaje": "Sede requerida."}, status=400)
        try:
            data = AdminVentasService().buscar_productos(q, id_sede)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class PosEmitirView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_POS_CREAR

    @extend_schema(operation_id="pos_emitir_factura")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminVentasService().emitir(_ctx(request), body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class FacturasListView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_FACTURAS_VER

    @extend_schema(operation_id="facturas_listar")
    def get(self, request: Request) -> Response:
        filtros = {k: str(v) for k, v in request.query_params.items()}
        page = int(request.query_params.get("page") or 1)
        page_size = int(request.query_params.get("page_size") or 20)
        try:
            data = AdminVentasService().listar(_ctx(request), filtros, page, page_size)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class FacturaDetailView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_FACTURAS_TOTAL if self.request.method != "GET" else PERM_FACTURAS_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="facturas_detalle")
    def get(self, request: Request, pk: int) -> Response:
        try:
            data = AdminVentasService().obtener(_ctx(request), pk)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)

    @extend_schema(operation_id="facturas_editar")
    def patch(self, request: Request, pk: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminVentasService().editar(_ctx(request), pk, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class FacturaAnularView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_FACTURAS_TOTAL

    @extend_schema(operation_id="facturas_anular")
    def post(self, request: Request, pk: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminVentasService().anular(_ctx(request), pk, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class FacturaDevolucionView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_FACTURAS_TOTAL

    @extend_schema(operation_id="facturas_devolucion")
    def post(self, request: Request, pk: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminVentasService().devolucion(_ctx(request), pk, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)