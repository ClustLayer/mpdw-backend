from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m21_promociones.admin_promociones_service import AdminPromocionesService
from apps.m21_promociones.mensajes import MSG_ARCHIVO
from apps.m21_promociones.models import Promociones
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError

PERM_VER = ("promociones", "Consultar")
PERM_CREAR = ("promociones", "Crear")
PERM_EDITAR = ("promociones", "Editar")


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


class PromocionesPublicasView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(operation_id="promociones_publicas")
    def get(self, request: Request) -> Response:
        return Response(AdminPromocionesService().publicas())


class PromocionAdminListCreateView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_CREAR if self.request.method == "POST" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="promociones_listar")
    def get(self, request: Request) -> Response:
        q = str(request.query_params.get("q") or "")
        estado = str(request.query_params.get("estado") or "todos")
        page = int(request.query_params.get("page") or 1)
        page_size = min(100, int(request.query_params.get("page_size") or 20))
        try:
            data = AdminPromocionesService().listar(q, estado, page, page_size)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)

    @extend_schema(operation_id="promociones_crear")
    def post(self, request: Request) -> Response:
        try:
            data = AdminPromocionesService().crear(_ctx(request), dict(request.data))
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class PromocionAdminDetailView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_EDITAR if self.request.method in {"PUT", "PATCH"} else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="promociones_detalle")
    def get(self, request: Request, pk: int) -> Response:
        try:
            data = AdminPromocionesService().obtener(pk)
        except Promociones.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(data)

    @extend_schema(operation_id="promociones_actualizar")
    def put(self, request: Request, pk: int) -> Response:
        try:
            data = AdminPromocionesService().actualizar(_ctx(request), pk, dict(request.data))
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)

    def patch(self, request: Request, pk: int) -> Response:
        return self.put(request, pk)


class PromocionImagenView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(operation_id="promociones_imagen")
    def post(self, request: Request, pk: int) -> Response:
        archivo = request.FILES.get("imagen") or request.FILES.get("archivo")
        if not archivo:
            return Response({"mensaje": MSG_ARCHIVO, "codigo": "ARCHIVO_INVALIDO"}, status=400)
        contenido = archivo.read()
        mime = archivo.content_type or "application/octet-stream"
        try:
            ruta = AdminPromocionesService().guardar_imagen(pk, archivo.name, contenido, mime)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response({"imagen": ruta, "mensaje": "Imagen guardada."})
