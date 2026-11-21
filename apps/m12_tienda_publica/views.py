"""API pública de tienda (Épica 16)."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m12_tienda_publica.escaparate_service import EscaparateService
from apps.m12_tienda_publica.tienda_catalogo_service import TiendaCatalogoService
from apps.m12_tienda_publica.tienda_pedido_service import TiendaPedidoService
from contratos.excepciones import ReglaNegocioError


def _err(exc: ReglaNegocioError, request: Request) -> Response:
    code: int = status.HTTP_400_BAD_REQUEST
    if exc.codigo == "NO_ENCONTRADO":
        code = status.HTTP_404_NOT_FOUND
    elif exc.codigo in {"VALIDACION", "TELEFONO_INVALIDO", "CARRITO_VACIO", "URL_LARGA", "SIN_WHATSAPP", "SIN_NUMERO"}:
        code = status.HTTP_400_BAD_REQUEST
    return Response(
        {
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": exc.detalles,
            "idCorrelacion": getattr(request, "correlation_id", ""),
        },
        status=code,
    )


def _int_q(request: Request, key: str, default: int = 0) -> int:
    raw = request.query_params.get(key)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class TiendaFiltrosView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="tienda_filtros", tags=["tienda-publica"])
    def get(self, request: Request) -> Response:
        return Response(TiendaCatalogoService().filtros())


class TiendaCatalogoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="tienda_catalogo", tags=["tienda-publica"])
    def get(self, request: Request) -> Response:
        page = max(1, _int_q(request, "page", 1))
        page_size = min(48, max(1, _int_q(request, "page_size", 12)))
        id_sede = _int_q(request, "id_sede", 0) or None
        try:
            data = TiendaCatalogoService().listar(
                q=request.query_params.get("q"),
                id_categoria=_int_q(request, "id_categoria", 0) or None,
                id_marca=_int_q(request, "id_marca", 0) or None,
                id_tipo=_int_q(request, "id_tipo", 0) or None,
                precio_min=request.query_params.get("precio_min"),
                precio_max=request.query_params.get("precio_max"),
                orden=request.query_params.get("orden"),
                page=page,
                page_size=page_size,
                id_sede=id_sede,
            )
            return Response(data)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        except Exception:
            from apps.m12_tienda_publica import mensajes as msg

            return Response({"mensaje": msg.MSG_CATALOGO_FALLA}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class TiendaProductoDetalleView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="tienda_producto_detalle", tags=["tienda-publica"])
    def get(self, request: Request, slug: str) -> Response:
        id_sede = _int_q(request, "id_sede", 0) or None
        try:
            return Response(TiendaCatalogoService().detalle(slug, id_sede))
        except ReglaNegocioError as exc:
            return _err(exc, request)
        except Exception:
            from apps.m12_tienda_publica import mensajes as msg

            return Response({"mensaje": msg.MSG_PRODUCTO_FALLA}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class TiendaValidarCarritoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="tienda_validar_carrito", tags=["tienda-publica"])
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        id_sede = int(body.get("id_sede") or 0) or None
        items = body.get("items") or []
        if not isinstance(items, list):
            items = []
        try:
            return Response(TiendaPedidoService().validar_carrito(id_sede, items))
        except ReglaNegocioError as exc:
            return _err(exc, request)
        except Exception:
            from apps.m12_tienda_publica import mensajes as msg

            return Response({"mensaje": msg.MSG_CARRITO_VALIDAR_FALLA}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class TiendaSedesView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="tienda_sedes", tags=["tienda-publica"])
    def get(self, request: Request) -> Response:
        return Response(TiendaPedidoService().sedes_activas())


class TiendaContactoWhatsappView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="tienda_contacto_whatsapp", tags=["tienda-publica"])
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        id_sede = int(body.get("id_sede") or 0) or None
        texto = body.get("texto")
        try:
            return Response(TiendaPedidoService().contacto_whatsapp(id_sede, texto))
        except ReglaNegocioError as exc:
            return _err(exc, request)
        except Exception:
            from apps.m12_tienda_publica import mensajes as msg

            return Response({"mensaje": msg.MSG_WHATSAPP_FALLA}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class TiendaEscaparatesView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="tienda_escaparates", tags=["tienda-publica"])
    def get(self, request: Request) -> Response:
        id_sede = _int_q(request, "id_sede", 0) or None
        return Response(EscaparateService().listar_publico(id_sede))


class TiendaPrepararPedidoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="tienda_preparar_pedido", tags=["tienda-publica"])
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            return Response(TiendaPedidoService().preparar_pedido(body), status=status.HTTP_201_CREATED)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        except Exception:
            from apps.m12_tienda_publica import mensajes as msg

            return Response({"mensaje": msg.MSG_PEDIDO_FALLA}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
