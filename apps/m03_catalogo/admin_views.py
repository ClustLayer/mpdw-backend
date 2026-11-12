import logging
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m03_catalogo.admin_catalogo_service import AdminCatalogoService
from apps.m03_catalogo.mensajes import MSG_CARGA_ERROR, MSG_HISTORIAL_ERROR
from apps.m03_catalogo.models import Categorias_producto, Marcas, Productos, Tipos_producto
from contratos.dtos import AuthContext
from contratos.excepciones import DominioError, ReglaNegocioError

logger = logging.getLogger(__name__)
PERM_VER = ("catalogo_productos", "Consultar")
PERM_CREAR = ("catalogo_productos", "Crear")
PERM_EDITAR = ("catalogo_productos", "Editar")
PERM_ESTADO = ("catalogo_productos", "Cambiar estado")
PERM_EXPORT = ("catalogo_productos", "Exportar")


def _ctx(request: Request) -> AuthContext:
    ctx = getattr(request, "auth_context", None)
    if not isinstance(ctx, AuthContext):  # pragma: no cover
        raise ReglaNegocioError("Contexto de autenticacion ausente.", codigo="NO_AUTORIZADO")
    return ctx


def _err(exc: ReglaNegocioError | DominioError, request: Request) -> Response:
    code: int = status.HTTP_400_BAD_REQUEST
    if exc.codigo == "NO_AUTORIZADO":  # pragma: no cover
        code = status.HTTP_403_FORBIDDEN
    elif exc.codigo == "CONCURRENCIA":
        code = status.HTTP_409_CONFLICT
    return Response(
        {
            "codigo": "CONFLICTO_CONCURRENCIA" if exc.codigo == "CONCURRENCIA" else exc.codigo,
            "mensaje": exc.mensaje,
            "detalles": [],
            "idCorrelacion": getattr(request, "correlation_id", ""),
        },
        status=code,
    )


def _svc() -> AdminCatalogoService:
    return AdminCatalogoService()


class ProductoAdminListCreateView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_CREAR if self.request.method == "POST" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    @extend_schema(operation_id="catalogo_productos_list")
    def get(self, request: Request) -> Response:
        params = request.query_params
        try:
            page = max(1, int(params.get("page") or 1))
            page_size = min(50, max(1, int(params.get("page_size") or 10)))
        except (TypeError, ValueError):
            return Response({"codigo": "PAGINACION_INVALIDA", "mensaje": "Paginación inválida."}, status=400)
        try:
            body = _svc().listar(
                q=params.get("q") or "",
                filtros={
                    "id_categoria": params.get("id_categoria") or "",
                    "id_marca": params.get("id_marca") or "",
                    "id_tipo": params.get("id_tipo") or "",
                    "estado": params.get("estado") or "todos",
                    "stock": params.get("stock") or "todos",
                },
                page=page,
                page_size=page_size,
                orden=params.get("orden") or "nombre",
            )
            body["catalogos"] = _svc().catalogos_activos()
            return Response(body)
        except Exception:  # pragma: no cover
            logger.exception("listar productos")
            return Response({"codigo": "CARGA_ERROR", "mensaje": MSG_CARGA_ERROR}, status=500)

    @extend_schema(operation_id="catalogo_productos_create")
    def post(self, request: Request) -> Response:
        try:
            cuerpo = request.data if isinstance(request.data, dict) else {}
            data, mensaje = _svc().crear(_ctx(request), cuerpo)
            return Response({"mensaje": mensaje, "producto": data}, status=201)
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class ProductoAdminDetailView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_EDITAR if self.request.method == "PATCH" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    def get(self, request: Request, pk: int) -> Response:
        try:
            return Response(_svc().detalle(pk))
        except Productos.DoesNotExist:
            return Response({"codigo": "NO_ENCONTRADO", "mensaje": "Producto no encontrado."}, status=404)

    def patch(self, request: Request, pk: int) -> Response:
        self.required_permission = PERM_EDITAR
        try:
            cuerpo = request.data if isinstance(request.data, dict) else {}
            data, mensaje = _svc().editar(_ctx(request), pk, cuerpo)
            return Response({"mensaje": mensaje, "producto": data})
        except Productos.DoesNotExist:  # pragma: no cover
            return Response({"codigo": "NO_ENCONTRADO", "mensaje": "Producto no encontrado."}, status=404)
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class ProductoEstadoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_ESTADO

    def post(self, request: Request, pk: int) -> Response:
        try:
            cuerpo = request.data if isinstance(request.data, dict) else {}
            mensaje = _svc().cambiar_estado(_ctx(request), pk, bool(cuerpo.get("activo")))
            return Response({"mensaje": mensaje})
        except Productos.DoesNotExist:
            return Response({"codigo": "NO_ENCONTRADO", "mensaje": "Producto no encontrado."}, status=404)
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class HistorialPreciosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_VER

    def get(self, request: Request, pk: int) -> Response:
        try:
            return Response(_svc().historial(pk, request.query_params.get("desde") or "", request.query_params.get("hasta") or ""))
        except Productos.DoesNotExist:
            return Response({"codigo": "NO_ENCONTRADO", "mensaje": "Producto no encontrado."}, status=404)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        except Exception:  # pragma: no cover
            logger.exception("historial")
            return Response({"codigo": "HISTORIAL_ERROR", "mensaje": MSG_HISTORIAL_ERROR}, status=500)


class CatalogoImagenView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request, pk: int) -> Response:
        archivo = request.FILES.get("imagen")
        if not archivo:
            from apps.m03_catalogo.mensajes import MSG_ARCHIVO

            return Response({"codigo": "ARCHIVO_INVALIDO", "mensaje": MSG_ARCHIVO}, status=400)
        try:
            ruta = _svc().guardar_imagen(pk, archivo.name, archivo.read(), archivo.content_type or "")
            return Response({"imagen_url": ruta, "mensaje": "Imagen cargada."})  # pragma: no cover
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class CatalogoParametrosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]

    def get_permissions(self):
        self.required_permission = PERM_CREAR if self.request.method == "POST" else PERM_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    def get(self, request: Request, tipo: str) -> Response:
        if tipo not in {"categorias", "marcas", "tipos"}:
            return Response({"codigo": "TIPO", "mensaje": "Parámetro no válido."}, status=400)
        return Response({"items": _svc().listar_param(tipo)})

    def post(self, request: Request, tipo: str) -> Response:
        if tipo not in {"categorias", "marcas", "tipos"}:
            return Response({"codigo": "TIPO", "mensaje": "Parámetro no válido."}, status=400)
        try:
            cuerpo = request.data if isinstance(request.data, dict) else {}
            return Response({"mensaje": _svc().crear_param(_ctx(request), tipo, cuerpo)}, status=201)
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class ParametroDetalleView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EDITAR

    def patch(self, request: Request, tipo: str, pk: int) -> Response:
        modelos = {"categorias": Categorias_producto, "marcas": Marcas, "tipos": Tipos_producto}
        if tipo not in modelos:
            return Response({"codigo": "TIPO", "mensaje": "Parámetro no válido."}, status=400)
        try:
            cuerpo = request.data if isinstance(request.data, dict) else {}
            return Response({"mensaje": _svc().editar_param(_ctx(request), tipo, pk, cuerpo)})
        except modelos[tipo].DoesNotExist:  # type: ignore[attr-defined]
            return Response({"codigo": "NO_ENCONTRADO", "mensaje": "Registro no encontrado."}, status=404)
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class ImportarProductosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CREAR
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        archivo = request.FILES.get("archivo")
        if not archivo:
            from apps.m03_catalogo.mensajes import MSG_IMPORT_FORMATO

            return Response({"codigo": "FORMATO_ARCHIVO", "mensaje": MSG_IMPORT_FORMATO}, status=400)
        try:
            return Response(_svc().importar(_ctx(request), archivo.name, archivo.read()))
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class PlantillaImportView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CREAR

    def get(self, request: Request) -> HttpResponse:
        contenido = _svc().plantilla_xlsx()
        resp = HttpResponse(
            contenido,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = 'attachment; filename="plantilla-productos.xlsx"'
        return resp


class ExportarProductosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_EXPORT

    def get(self, request: Request) -> Response | HttpResponse:
        formato = (request.query_params.get("formato") or "").lower()
        if formato not in {"csv", "xlsx"}:
            return Response({"codigo": "FORMATO", "mensaje": "Seleccione Excel o CSV."}, status=400)
        try:
            nombre, contenido, mime = _svc().exportar(
                request.query_params.get("q") or "",
                {
                    "id_categoria": request.query_params.get("id_categoria") or "",
                    "id_marca": request.query_params.get("id_marca") or "",
                    "id_tipo": request.query_params.get("id_tipo") or "",
                    "estado": request.query_params.get("estado") or "todos",
                    "stock": request.query_params.get("stock") or "todos",
                },
                formato,
            )
            resp = HttpResponse(contenido, content_type=mime)
            resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
            resp["X-Mensaje"] = "Exportación generada correctamente."
            return resp
        except (ReglaNegocioError, DominioError) as exc:
            return _err(exc, request)


class ProductoMediaView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request: Request, ruta: str) -> FileResponse | Response:
        base = (Path(settings.BASE_DIR) / "media").resolve()
        objetivo = (base / ruta).resolve()
        if not str(objetivo).startswith(str(base)) or not objetivo.is_file():
            return Response(status=404)
        return FileResponse(objetivo.open("rb"))  # pragma: no cover
