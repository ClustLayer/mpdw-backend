import logging

from django.db import models
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.admin_roles_permisos_service import AdminRolesPermisosService
from apps.m01_identidad.admin_roles_serializers import (
    AccesosPanelResponseSerializer,
    CatalogosPermisoResponseSerializer,
    CrearPermisoRequestSerializer,
    CrearRolRequestSerializer,
    EditarPermisoRequestSerializer,
    EditarRolRequestSerializer,
    GuardarMatrizRequestSerializer,
    MatrizResponseSerializer,
    PermisoListItemSerializer,
    PermisoListResponseSerializer,
    RolDetalleResponseSerializer,
    RolListResponseSerializer,
    UsuarioCatalogoResponseSerializer,
)
from apps.m01_identidad.admin_serializers import RolesCatalogoResponseSerializer
from apps.m01_identidad.models import Permisos, Roles, Usuarios
from apps.m01_identidad.panel_resumen_service import construir_panel_resumen
from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m01_identidad.serializers import MensajeResponseSerializer
from apps.m01_identidad.services import PermissionService
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuthContext
from contratos.excepciones import DominioError, ReglaNegocioError

logger = logging.getLogger(__name__)

PERM_ROLES = ("roles_permisos", "T")


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


def _page_params(params, request: Request) -> tuple[int, int] | Response:
    try:
        page = max(1, int(params.get("page") or 1))
        page_size = min(100, max(1, int(params.get("page_size") or 20)))
        return page, page_size
    except (TypeError, ValueError):
        return _error(
            "PAGINACION_INVALIDA",
            "Los parámetros page y page_size deben ser números enteros válidos.",
            status.HTTP_400_BAD_REQUEST,
            request,
        )


def _dominio(exc: ReglaNegocioError | DominioError, request: Request) -> Response:
    http_status_code: int = status.HTTP_400_BAD_REQUEST
    if exc.codigo in {"ROL_NO_ENCONTRADO", "PERMISO_NO_ENCONTRADO"}:
        http_status_code = status.HTTP_404_NOT_FOUND
    elif exc.codigo in {"NO_AUTORIZADO", "ROL_BASE_PROTEGIDO"}:
        http_status_code = status.HTTP_403_FORBIDDEN
    elif exc.codigo in {"CONCURRENCIA", "CONFLICTO_CONCURRENCIA"}:
        http_status_code = status.HTTP_409_CONFLICT
    codigo_resp = exc.codigo
    if codigo_resp == "CONCURRENCIA":
        codigo_resp = "CONFLICTO_CONCURRENCIA"
    return _error(codigo_resp, exc.mensaje, http_status_code, request)


def _svc() -> AdminRolesPermisosService:
    return AdminRolesPermisosService(audit_port=AuditService())


class RolListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_ROLES

    @extend_schema(operation_id="roles_list", responses={200: RolListResponseSerializer})
    def get(self, request: Request) -> Response:
        params = request.query_params
        parsed = _page_params(params, request)
        if isinstance(parsed, Response):
            return parsed
        page, page_size = parsed
        pagina = _svc().listar_roles(
            q=params.get("q", ""),
            estado_filtro=params.get("estado") or "todos",
            page=page,
            page_size=page_size,
        )
        return Response(
            {
                "items": pagina.items,
                "total": pagina.total,
                "page": pagina.page,
                "page_size": pagina.page_size,
                "mensaje": pagina.mensaje,
            }
        )

    @extend_schema(
        operation_id="roles_create",
        request=CrearRolRequestSerializer,
        responses={201: RolDetalleResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        ser = CrearRolRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            detalle, mensaje = _svc().crear_rol(_ctx(request), ser.validated_data)
            return Response({**detalle, "mensaje": mensaje}, status=status.HTTP_201_CREATED)
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)


class RolDetailView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_ROLES

    @extend_schema(operation_id="roles_detail", responses={200: RolDetalleResponseSerializer})
    def get(self, request: Request, id_rol: int) -> Response:
        try:
            detalle = _svc().detalle_rol(id_rol)
            return Response(detalle)
        except Roles.DoesNotExist:
            return _error(
                "ROL_NO_ENCONTRADO", "Rol no encontrado.", status.HTTP_404_NOT_FOUND, request
            )

    @extend_schema(
        operation_id="roles_update",
        request=EditarRolRequestSerializer,
        responses={200: RolDetalleResponseSerializer},
    )
    def patch(self, request: Request, id_rol: int) -> Response:
        ser = EditarRolRequestSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            detalle, mensaje = _svc().editar_rol(_ctx(request), id_rol, ser.validated_data)
            return Response({**detalle, "mensaje": mensaje})
        except Roles.DoesNotExist:
            return _error(
                "ROL_NO_ENCONTRADO", "Rol no encontrado.", status.HTTP_404_NOT_FOUND, request
            )
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)

    @extend_schema(operation_id="roles_delete", responses={200: MensajeResponseSerializer})
    def delete(self, request: Request, id_rol: int) -> Response:
        try:
            mensaje = _svc().eliminar_rol(_ctx(request), id_rol)
            return Response({"mensaje": mensaje})
        except Roles.DoesNotExist:
            return _error(
                "ROL_NO_ENCONTRADO", "Rol no encontrado.", status.HTTP_404_NOT_FOUND, request
            )
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)


class PermisoListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_ROLES

    @extend_schema(
        operation_id="permisos_catalog_list", responses={200: PermisoListResponseSerializer}
    )
    def get(self, request: Request) -> Response:
        params = request.query_params
        parsed = _page_params(params, request)
        if isinstance(parsed, Response):
            return parsed
        page, page_size = parsed
        pagina = _svc().listar_permisos(
            q=params.get("q", ""),
            modulo=params.get("modulo") or "",
            accion=params.get("accion") or "",
            estado_filtro=params.get("estado") or "todos",
            page=page,
            page_size=page_size,
        )
        return Response(
            {
                "items": pagina.items,
                "total": pagina.total,
                "page": pagina.page,
                "page_size": pagina.page_size,
                "mensaje": pagina.mensaje,
            }
        )

    @extend_schema(
        operation_id="permisos_create",
        request=CrearPermisoRequestSerializer,
        responses={201: MensajeResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        ser = CrearPermisoRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            _, mensaje = _svc().crear_permiso(_ctx(request), ser.validated_data)
            return Response({"mensaje": mensaje}, status=status.HTTP_201_CREATED)
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)


class PermisoDetailView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_ROLES

    @extend_schema(
        operation_id="permisos_update",
        request=EditarPermisoRequestSerializer,
        responses={200: PermisoListItemSerializer},
    )
    def patch(self, request: Request, id_permiso: int) -> Response:
        ser = EditarPermisoRequestSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            detalle, mensaje = _svc().editar_permiso(_ctx(request), id_permiso, ser.validated_data)
            return Response({**detalle, "mensaje": mensaje})
        except Permisos.DoesNotExist:
            return _error(
                "PERMISO_NO_ENCONTRADO",
                "Permiso no encontrado.",
                status.HTTP_404_NOT_FOUND,
                request,
            )
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)


class PermisoCatalogosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_ROLES

    @extend_schema(
        operation_id="permisos_catalogos", responses={200: CatalogosPermisoResponseSerializer}
    )
    def get(self, request: Request) -> Response:
        return Response(_svc().catalogos())


class MatrizPermisosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_ROLES

    @extend_schema(operation_id="matriz_get", responses={200: MatrizResponseSerializer})
    def get(self, request: Request) -> Response:
        tipo = request.query_params.get("tipo") or ""
        id_raw = (
            request.query_params.get("id_destino")
            or request.query_params.get("id_rol")
            or request.query_params.get("id_usuario")
        )
        try:
            id_destino = int(id_raw or 0)
        except (TypeError, ValueError):
            return _error(
                "MATRIZ_DESTINO_INVALIDO",
                "El identificador de destino no es válido.",
                status.HTTP_400_BAD_REQUEST,
                request,
            )
        try:
            data = _svc().obtener_matriz(tipo, id_destino)
            return Response(data)
        except (ReglaNegocioError, Roles.DoesNotExist, Usuarios.DoesNotExist) as exc:
            if isinstance(exc, ReglaNegocioError):
                return _dominio(exc, request)
            return _error(
                "DESTINO_NO_ENCONTRADO",
                "Destino no encontrado.",
                status.HTTP_404_NOT_FOUND,
                request,
            )

    @extend_schema(
        operation_id="matriz_save",
        request=GuardarMatrizRequestSerializer,
        responses={200: MensajeResponseSerializer},
    )
    def put(self, request: Request) -> Response:
        ser = GuardarMatrizRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            mensaje = _svc().guardar_matriz(_ctx(request), ser.validated_data)
            return Response({"mensaje": mensaje})
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)


class RolesActivosCatalogoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_ROLES

    @extend_schema(
        operation_id="roles_activos_catalogo", responses={200: RolesCatalogoResponseSerializer}
    )
    def get(self, request: Request) -> Response:
        roles = Roles.objects.filter(estado=True).order_by("nombre").values("id_rol", "nombre")
        return Response({"items": list(roles)})


class UsuariosActivosCatalogoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_ROLES

    @extend_schema(
        operation_id="usuarios_activos_matriz",
        responses={200: UsuarioCatalogoResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        params = request.query_params
        parsed = _page_params(params, request)
        if isinstance(parsed, Response):
            return parsed
        page, page_size = parsed
        q = (params.get("q") or "").strip()
        qs = Usuarios.objects.filter(estado=True).select_related("id_rol").order_by(
            "nombre", "apellido"
        )
        if q:
            qs = qs.filter(
                models.Q(nombre__icontains=q)
                | models.Q(apellido__icontains=q)
                | models.Q(email__icontains=q)
            )
        total = qs.count()
        offset = (page - 1) * page_size
        items = [
            {
                "id_usuario": u.id_usuario,
                "label": f"{u.nombre} {u.apellido}".strip() or u.email,
                "rol": u.id_rol.nombre,
            }
            for u in qs[offset : offset + page_size]
        ]
        return Response(
            {"items": items, "total": total, "page": page, "page_size": page_size}
        )


class AccesosPanelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="auth_accesos_panel", responses={200: AccesosPanelResponseSerializer}
    )
    def get(self, request: Request) -> Response:
        ctx = _ctx(request)
        data = PermissionService().accesos_panel(ctx)
        return Response(data)


class PanelResumenView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="auth_panel_resumen")
    def get(self, request: Request) -> Response:
        ctx = _ctx(request)
        return Response(construir_panel_resumen(ctx))
