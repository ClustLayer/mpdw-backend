"""Administración de vitrinas del inicio (permisos catálogo de productos)."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m12_tienda_publica.escaparate_service import EscaparateService
from contratos.excepciones import ReglaNegocioError

PERM_VER = ("catalogo_productos", "Consultar")
PERM_CREAR = ("catalogo_productos", "Crear")
PERM_EDITAR = ("catalogo_productos", "Editar")


def _err(exc: ReglaNegocioError) -> Response:
    code = 400
    if exc.codigo == "NO_ENCONTRADO":
        code = 404
    elif exc.codigo == "CONFLICTO":
        code = 409
    return Response({"codigo": exc.codigo, "mensaje": exc.mensaje}, status=code)


class EscaparateAdminListView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]

    def get_permissions(self):
        if self.request.method == "POST":
            self.required_permission = PERM_CREAR
        else:
            self.required_permission = PERM_VER
        return super().get_permissions()

    @extend_schema(tags=["catalogo-escaparates"])
    def get(self, request: Request) -> Response:
        return Response(EscaparateService().listar_admin())

    @extend_schema(tags=["catalogo-escaparates"])
    def post(self, request: Request) -> Response:
        try:
            return Response(EscaparateService().crear(request.data), status=201)
        except ReglaNegocioError as exc:
            return _err(exc)


class EscaparateAdminDetailView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR

    @extend_schema(tags=["catalogo-escaparates"])
    def patch(self, request: Request, pk: int) -> Response:
        try:
            return Response(EscaparateService().actualizar(pk, request.data))
        except ReglaNegocioError as exc:
            return _err(exc)


class EscaparateProductosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR

    @extend_schema(tags=["catalogo-escaparates"])
    def post(self, request: Request, pk: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        ids = body.get("ids_producto") or body.get("productos") or []
        try:
            ids_int = [int(x) for x in ids]
        except (TypeError, ValueError):
            return Response({"mensaje": "Lista de productos inválida."}, status=400)
        try:
            return Response(EscaparateService().asignar_productos(pk, ids_int))
        except ReglaNegocioError as exc:
            return _err(exc)
