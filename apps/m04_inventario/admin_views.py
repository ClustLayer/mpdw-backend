from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m04_inventario.admin_service import AdminInventarioService
from contratos.dtos import AuthContext
from contratos.excepciones import DominioError, ReglaNegocioError

PERM = ("inventario_kardex", "Consultar")
PERM_W = ("inventario_kardex", "Crear")


def _ctx(request: Request) -> AuthContext:
    ctx = getattr(request, "auth_context", None)
    if not isinstance(ctx, AuthContext):
        raise ReglaNegocioError("Contexto de autenticacion ausente.", codigo="NO_AUTORIZADO")
    return ctx


class ExistenciasView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM

    @extend_schema(operation_id="inventario_existencias")
    def get(self, request: Request) -> Response:
        q = str(request.query_params.get("q") or "")
        sede = request.query_params.get("id_sede")
        data = AdminInventarioService().existencias(q, int(sede) if sede else None)
        return Response(data)


class KardexView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM

    @extend_schema(operation_id="inventario_kardex")
    def get(self, request: Request) -> Response:
        filtros = {k: str(request.query_params.get(k) or "") for k in ("id_sede", "tipo", "desde", "hasta")}
        return Response(AdminInventarioService().kardex(filtros))


class ProductosOpcionesView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM

    @extend_schema(operation_id="inventario_productos_opciones")
    def get(self, request: Request) -> Response:
        q = str(request.query_params.get("q") or "")
        return Response(AdminInventarioService().productos_opciones(q))


class EntradaLoteView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_W

    @extend_schema(operation_id="inventario_entrada_lote")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        svc = AdminInventarioService()
        try:
            msg = svc.entrada_lote(_ctx(request), body)
        except (ReglaNegocioError, DominioError) as exc:
            return Response({"mensaje": exc.mensaje, "codigo": exc.codigo}, status=400)
        return Response({"mensaje": msg}, status=201)


class MovimientoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_W

    @extend_schema(operation_id="inventario_movimiento")
    def post(self, request: Request, accion: str) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        svc = AdminInventarioService()
        try:
            ctx = _ctx(request)
            if accion == "entrada":
                msg = svc.entrada(ctx, body)
            elif accion == "ajuste":
                msg = svc.ajuste(ctx, body)
            elif accion == "traslado":
                msg = svc.traslado(ctx, body)
            else:
                return Response({"mensaje": "Accion no admitida."}, status=404)
        except (ReglaNegocioError, DominioError) as exc:
            return Response({"mensaje": exc.mensaje, "codigo": exc.codigo}, status=400)
        return Response({"mensaje": msg}, status=201)
