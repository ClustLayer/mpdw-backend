# ==============================================================================
# API REST administracion de usuarios - Epic 2
# ==============================================================================
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.admin_serializers import (
    CambiarEstadoRequestSerializer,
    ContrasenaTemporalResponseSerializer,
    CrearUsuarioRequestSerializer,
    EditarUsuarioRequestSerializer,
    RolesCatalogoResponseSerializer,
    UsuarioDetalleSerializer,
    UsuarioListResponseSerializer,
)
from apps.m01_identidad.admin_usuarios_service import AdminUsuariosService
from apps.m01_identidad.mensajes import MSG_LISTADO_ERROR
from apps.m01_identidad.models import Roles
from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m01_identidad.serializers import MensajeResponseSerializer
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuthContext
from contratos.excepciones import DominioError, ReglaNegocioError

logger = logging.getLogger(__name__)


def _correo():
    from apps.m13_plataforma.adapters.correo_factory import construir_adaptador_correo

    return construir_adaptador_correo()


def _ctx(request: Request) -> AuthContext:
    ctx: AuthContext | None = getattr(request, "auth_context", None)
    if ctx is None:
        raise ReglaNegocioError("Contexto de autenticacion ausente.", codigo="NO_AUTORIZADO")
    return ctx


def _error(codigo: str, mensaje: str, http_status: int, request: Request) -> Response:
    cid = getattr(request, "correlation_id", "")
    return Response(
        {"codigo": codigo, "mensaje": mensaje, "detalles": [], "idCorrelacion": cid},
        status=http_status,
    )


def _dominio(exc: ReglaNegocioError | DominioError, request: Request) -> Response:
    http_status_code: int = status.HTTP_400_BAD_REQUEST
    if exc.codigo in {"USUARIO_NO_ENCONTRADO"}:
        http_status_code = status.HTTP_404_NOT_FOUND
    elif exc.codigo in {"NO_AUTORIZADO", "CONTRASENA_TEMP_PROPIA", "ROL_PROPIO"}:
        http_status_code = status.HTTP_403_FORBIDDEN
    elif exc.codigo in {"EMAIL_NO_ENTREGADO"}:
        http_status_code = status.HTTP_502_BAD_GATEWAY
    return _error(exc.codigo, exc.mensaje, http_status_code, request)


class UsuarioListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("usuarios", "T")

    @extend_schema(
        operation_id="usuarios_admin_list",
        summary="Listar usuarios",
        responses={200: UsuarioListResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        params = request.query_params
        id_rol_raw = params.get("id_rol")
        id_rol: int | None = None
        if id_rol_raw:
            try:
                id_rol = int(str(id_rol_raw))
            except ValueError:
                id_rol = None
        try:
            page = int(params.get("page") or 1)
            page_size = int(params.get("page_size") or 20)
        except ValueError:
            page, page_size = 1, 20
        try:
            pagina = AdminUsuariosService(audit_port=AuditService(), email_port=_correo()).listar(
                q=str(params.get("q") or ""),
                id_rol=id_rol,
                estado_filtro=str(params.get("estado") or "todos"),
                page=page,
                page_size=page_size,
                ordering=str(params.get("ordering") or "-ultimo_acceso"),
            )
        except Exception:
            logger.exception("Fallo al listar usuarios")
            return _error(
                "LISTADO_USUARIOS",
                MSG_LISTADO_ERROR,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                request,
            )
        return Response(
            {
                "items": pagina.items,
                "total": pagina.total,
                "page": pagina.page,
                "page_size": pagina.page_size,
                "mensaje": pagina.mensaje,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="usuarios_admin_create",
        summary="Crear usuario",
        request=CrearUsuarioRequestSerializer,
        responses={201: UsuarioDetalleSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CrearUsuarioRequestSerializer(data=request.data)
        if not serializer.is_valid():
            exc = ReglaNegocioError(str(serializer.errors), codigo="DATOS_INVALIDOS")
            return _dominio(exc, request)
        try:
            mensaje, detalle = AdminUsuariosService(
                audit_port=AuditService(), email_port=_correo()
            ).crear(_ctx(request), serializer.validated_data)
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)
        return Response({"mensaje": mensaje, **detalle}, status=status.HTTP_201_CREATED)


class UsuarioDetailView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("usuarios", "T")

    @extend_schema(
        operation_id="usuarios_admin_detail",
        summary="Detalle de usuario",
        responses={200: UsuarioDetalleSerializer},
    )
    def get(self, request: Request, id_usuario: int) -> Response:
        try:
            detalle = AdminUsuariosService().obtener_detalle(id_usuario)
        except ReglaNegocioError as exc:
            return _dominio(exc, request)
        ctx = _ctx(request)
        if detalle["id_usuario"] == ctx.id_usuario:
            detalle["puede_contrasena_temporal"] = False
        return Response(detalle, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="usuarios_admin_update",
        summary="Editar usuario",
        request=EditarUsuarioRequestSerializer,
        responses={200: UsuarioDetalleSerializer},
    )
    def patch(self, request: Request, id_usuario: int) -> Response:
        serializer = EditarUsuarioRequestSerializer(data=request.data)
        if not serializer.is_valid():
            exc = ReglaNegocioError(str(serializer.errors), codigo="DATOS_INVALIDOS")
            return _dominio(exc, request)
        try:
            mensaje, detalle = AdminUsuariosService(audit_port=AuditService()).actualizar(
                _ctx(request), id_usuario, serializer.validated_data
            )
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)
        return Response({"mensaje": mensaje, **detalle}, status=status.HTTP_200_OK)


class UsuarioEstadoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("usuarios", "T")

    @extend_schema(
        operation_id="usuarios_admin_estado",
        summary="Cambiar estado de usuario",
        request=CambiarEstadoRequestSerializer,
        responses={200: MensajeResponseSerializer},
    )
    def post(self, request: Request, id_usuario: int) -> Response:
        serializer = CambiarEstadoRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _dominio(
                ReglaNegocioError(str(serializer.errors), codigo="DATOS_INVALIDOS"), request
            )
        try:
            mensaje = AdminUsuariosService(audit_port=AuditService()).cambiar_estado(
                _ctx(request), id_usuario, serializer.validated_data["accion"]
            )
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)
        return Response({"mensaje": mensaje}, status=status.HTTP_200_OK)


class UsuarioContrasenaTemporalView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("usuarios", "T")

    @extend_schema(
        operation_id="usuarios_admin_contrasena_temporal",
        summary="Generar contraseña temporal",
        request=None,
        responses={200: ContrasenaTemporalResponseSerializer},
    )
    def post(self, request: Request, id_usuario: int) -> Response:
        try:
            mensaje, clave = AdminUsuariosService(
                audit_port=AuditService()
            ).generar_contrasena_temporal(_ctx(request), id_usuario)
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)
        return Response(
            {
                "mensaje": mensaje,
                "contrasena_temporal": clave,
                "leyenda": "Esta contraseña no se volverá a mostrar.",
            },
            status=status.HTTP_200_OK,
        )


class RolesCatalogoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("usuarios", "T")

    @extend_schema(
        operation_id="usuarios_roles_catalogo",
        summary="Roles activos para formularios de usuario",
        responses={200: RolesCatalogoResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        roles = Roles.objects.filter(estado=True).order_by("nombre").values("id_rol", "nombre")
        return Response({"items": list(roles)}, status=status.HTTP_200_OK)
