from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m08_caja.admin_caja_service import AdminCajaService
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError

PERM_VER = ("cuentas_bancarias", "Consultar")
PERM_CREAR = ("cuentas_bancarias", "Crear")
PERM_EDITAR = ("cuentas_bancarias", "Editar")


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
        {"codigo": exc.codigo, "mensaje": exc.mensaje, "idCorrelacion": getattr(request, "correlation_id", "")},
        status=code,
    )


class CuentasActivasView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    @extend_schema(operation_id="cuentas_activas")
    def get(self, request: Request) -> Response:
        return Response(AdminCajaService().listar_activas())


class CuentasListCreateView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_CREAR if self.request.method == "POST" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="cuentas_listar")
    def get(self, request: Request) -> Response:
        page = max(1, int(request.query_params.get("page") or 1))
        page_size = min(100, max(1, int(request.query_params.get("page_size") or 20)))
        return Response(
            AdminCajaService().listar(
                str(request.query_params.get("q") or ""),
                request.query_params.get("estado"),
                page,
                page_size,
            )
        )

    @extend_schema(operation_id="cuentas_crear")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminCajaService().crear(_ctx(request), body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class CuentaDetailView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR

    @extend_schema(operation_id="cuentas_actualizar")
    def patch(self, request: Request, id_cuenta: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = AdminCajaService().actualizar(_ctx(request), id_cuenta, body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)
