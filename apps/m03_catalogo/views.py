# ==============================================================================
# Vistas del Catálogo de Productos - MPDW
# SAD Ref: M03, ADR-005, §9.1, IX-1, TX-06, TX-07, TX-11
# ==============================================================================
from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m03_catalogo.serializers import (
    ProductoCreateSerializer,
    ProductoResponseSerializer,
    ProductoUpdatePrecioSerializer,
)
from apps.m03_catalogo.services import ProductoService
from apps.m10_auditoria.services import AuditService
from apps.m13_plataforma.gestor_transaccion import GestorTransaccionDjango
from apps.m13_plataforma.pagination import StandardPagination
from contratos.dtos import AuthContext, StockInicialDTO


def _obtener_auth_context(request: Request) -> AuthContext:
    ctx = getattr(request, "auth_context", None)
    if isinstance(ctx, AuthContext):
        return ctx
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        from apps.m01_identidad.models import Usuario_sede

        sedes = tuple(
            Usuario_sede.objects.filter(id_usuario=user, estado=True).values_list("id_sede_id", flat=True)
        )
        rol_nombre = getattr(user.id_rol, "nombre", "") if getattr(user, "id_rol", None) else ""
        es_global = rol_nombre == "Administrador"
        auth_ctx = AuthContext(
            id_usuario=user.id_usuario,
            email=user.email,
            rol_nombre=rol_nombre,
            sedes_asignadas=sedes,
            es_global=es_global,
            ip=request.META.get("REMOTE_ADDR", "127.0.0.1"),
            user_agent=request.META.get("HTTP_USER_AGENT", "Unknown"),
            id_correlacion=getattr(request, "correlation_id", ""),
        )
        request.auth_context = auth_ctx  # type: ignore[attr-defined]
        return auth_ctx
    from rest_framework.exceptions import NotAuthenticated

    raise NotAuthenticated("No autenticado.")


class ProductoListCreateView(APIView):
    """Búsqueda paginada de productos (IX-1) y alta con inventario inicial (TX-07)."""

    pagination_class = StandardPagination

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = ProductoService(
            audit_port=AuditService(),
            tx_manager=GestorTransaccionDjango(),
        )

    @extend_schema(
        summary="Listar o buscar productos",
        description="Búsqueda paginada con trigramas y filtrado por categoría.",
        parameters=[
            OpenApiParameter("q", str, description="Término de búsqueda", required=False),
            OpenApiParameter("categoria", int, description="ID de la categoría", required=False),
        ],
        responses={200: ProductoResponseSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        termino = request.query_params.get("q")
        id_categoria = request.query_params.get("categoria")
        categoria_id = int(id_categoria) if id_categoria and id_categoria.isdigit() else None

        qs = self._service.listar_productos(termino=termino, id_categoria=categoria_id)

        paginator = self.pagination_class()
        page: Any = paginator.paginate_queryset(qs, request)
        serializer = ProductoResponseSerializer(page, many=True)
        return paginator.get_paginated_response(list(serializer.data))

    @extend_schema(
        summary="Crear producto",
        description="Alta de producto atómica con registro de existencias iniciales (TX-07).",
        request=ProductoCreateSerializer,
        responses={201: ProductoResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = ProductoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        stocks = [
            StockInicialDTO(id_sede=s["id_sede"], cantidad_inicial=s["cantidad_inicial"])
            for s in data.get("stocks_iniciales", [])
        ]

        ctx = _obtener_auth_context(request)

        producto = self._service.crear_producto(
            ctx=ctx,
            codigo_producto=data["codigo_producto"],
            codigo_barras=data.get("codigo_barras"),
            nombre=data["nombre"],
            descripcion=data.get("descripcion", ""),
            precio_venta=data["precio_venta"],
            id_categoria=data["id_categoria"],
            id_marca=data.get("id_marca"),
            id_tipo_producto=data.get("id_tipo_producto"),
            inventario_habilitado=data.get("inventario_habilitado", True),
            stocks_iniciales=stocks,
        )

        response_serializer = ProductoResponseSerializer(producto)
        response = Response(response_serializer.data, status=status.HTTP_201_CREATED)
        response["ETag"] = f'W/"{producto.version}"'
        return response


class ProductoPrecioUpdateView(APIView):
    """Actualización de precio con control de concurrencia optimista y motivo (TX-06, TX-11)."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = ProductoService(
            audit_port=AuditService(),
            tx_manager=GestorTransaccionDjango(),
        )

    @extend_schema(
        summary="Actualización de precio (PATCH)",
        description="Actualización con concurrencia optimista y motivo obligatorio (TX-06, TX-11).",
        request=ProductoUpdatePrecioSerializer,
        responses={200: ProductoResponseSerializer},
    )
    def patch(self, request: Request, pk: int) -> Response:
        return self._actualizar_precio(request, pk)

    @extend_schema(
        summary="Actualización de precio (PUT)",
        description="Actualización con concurrencia optimista y motivo obligatorio (TX-06, TX-11).",
        request=ProductoUpdatePrecioSerializer,
        responses={200: ProductoResponseSerializer},
    )
    def put(self, request: Request, pk: int) -> Response:
        return self._actualizar_precio(request, pk)

    def _actualizar_precio(self, request: Request, pk: int) -> Response:
        # Extraer versión desde la cabecera If-Match (ej. W/"3" o "3") o el cuerpo JSON
        version_header = request.headers.get("If-Match")
        version_val: int | None = None
        if version_header:
            version_clean = version_header.strip().strip('W/').strip('"')
            if version_clean.isdigit():
                version_val = int(version_clean)

        serializer_data: dict[str, Any] = request.data.copy() if isinstance(request.data, dict) else {}
        if version_val and "version" not in serializer_data:
            serializer_data["version"] = version_val

        serializer = ProductoUpdatePrecioSerializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)

        ctx = _obtener_auth_context(request)
        nuevo_precio = serializer.validated_data["nuevo_precio"]
        motivo = serializer.validated_data["motivo"]
        version = serializer.validated_data["version"]

        producto_actualizado = self._service.cambiar_precio(
            ctx=ctx,
            id_producto=pk,
            nuevo_precio=nuevo_precio,
            version=version,
            motivo=motivo,
        )

        response_serializer = ProductoResponseSerializer(producto_actualizado)
        response = Response(response_serializer.data, status=status.HTTP_200_OK)
        response["ETag"] = f'W/"{producto_actualizado.version}"'
        return response

