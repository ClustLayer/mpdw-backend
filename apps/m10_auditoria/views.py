# ==============================================================================
# API de consulta de bitácora de auditoría (solo lectura, HU 82)
# ==============================================================================
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m01_identidad.services import PermissionService
from apps.m10_auditoria.bitacora_service import BitacoraAuditoriaService
from apps.m10_auditoria.serializers import (
    AccionesBitacoraSerializer,
    BitacoraListResponseSerializer,
    UsuarioOpcionSerializer,
    UsuariosBitacoraQuerySerializer,
)
from contratos.dtos import AuthContext
from contratos.excepciones import DominioError, ReglaNegocioError

PERM_AUD_LEE = ("auditoria", "Consultar")


def _ctx(request: Request) -> AuthContext:
    ctx: AuthContext | None = getattr(request, "auth_context", None)
    if ctx is None:
        raise ReglaNegocioError("Contexto de autenticacion ausente.", codigo="NO_AUTORIZADO")
    return ctx


def _err(exc: ReglaNegocioError | DominioError, request: Request) -> Response:
    code: int = status.HTTP_400_BAD_REQUEST
    if exc.codigo == "NO_AUTORIZADO":
        code = status.HTTP_403_FORBIDDEN
    cid = getattr(request, "correlation_id", "")
    return Response(
        {"codigo": exc.codigo, "mensaje": exc.mensaje, "detalles": [], "idCorrelacion": cid},
        status=code,
    )


class BitacoraListView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_AUD_LEE

    @extend_schema(responses={200: BitacoraListResponseSerializer})
    def get(self, request: Request) -> Response:
        svc = BitacoraAuditoriaService()
        params = {k: request.query_params.get(k) for k in request.query_params}
        try:
            pag = svc.listar(params)
            body = {
                "items": pag.items,
                "total": pag.total,
                "page": pag.page,
                "page_size": pag.page_size,
                "mensaje": pag.mensaje,
            }
            return Response(body)
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class BitacoraAccionesView(APIView):
    """Acciones distintas registradas, para el filtro desplegable."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: AccionesBitacoraSerializer})
    def get(self, request: Request) -> Response:
        ctx = _ctx(request)
        if not PermissionService().tiene_permiso(ctx, "auditoria", "Consultar"):
            return Response(
                {
                    "codigo": "PERMISO_DENEGADO",
                    "mensaje": "No tiene permisos para realizar esta operación.",
                    "detalles": [],
                    "idCorrelacion": getattr(request, "correlation_id", ""),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({"acciones": BitacoraAuditoriaService().acciones()})


class BitacoraUsuariosOpcionesView(APIView):
    """Opciones de usuario para filtro con búsqueda (CA 2.1)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UsuarioOpcionSerializer(many=True)})
    def get(self, request: Request) -> Response:
        ser = UsuariosBitacoraQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        ctx = _ctx(request)
        if not PermissionService().tiene_permiso(ctx, "auditoria", "Consultar"):
            return Response(
                {
                    "codigo": "PERMISO_DENEGADO",
                    "mensaje": "No tiene permisos para realizar esta operación.",
                    "detalles": [],
                    "idCorrelacion": getattr(request, "correlation_id", ""),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        items = BitacoraAuditoriaService().opciones_usuarios(
            ser.validated_data.get("q") or "",
            limit=int(ser.validated_data.get("limit") or 30),
        )
        return Response(items)
