from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.permissions import HasDynamicPermission
from apps.m08_caja.admin_views import _ctx, _err
from apps.m08_caja.caja_epic11_service import CajaEpic11Service
from contratos.excepciones import ReglaNegocioError

PERM_CAT_VER = ("categorias_movimientos", "Consultar")
PERM_CAT_EDIT = ("categorias_movimientos", "Crear")
PERM_CON_VER = ("gastos_frecuentes", "Consultar")
PERM_CON_EDIT = ("gastos_frecuentes", "Crear")
PERM_CIERRE_VER = ("cierre_jornada", "Consultar")
PERM_CIERRE_OP = ("cierre_jornada", "Crear")


class CategoriasListCreateView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_CAT_EDIT if self.request.method == "POST" else PERM_CAT_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    def get(self, request: Request) -> Response:
        return Response(
            CajaEpic11Service().listar_categorias(
                request.query_params.get("tipo"), str(request.query_params.get("q") or "")
            )
        )

    def post(self, request: Request) -> Response:
        try:
            data = CajaEpic11Service().crear_categoria(_ctx(request), request.data if isinstance(request.data, dict) else {})
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class CategoriaDetailView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("categorias_movimientos", "Editar")

    def patch(self, request: Request, pk: int) -> Response:
        try:
            data = CajaEpic11Service().actualizar_categoria(
                _ctx(request), pk, request.data if isinstance(request.data, dict) else {}
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class ConceptosListCreateView(APIView):
    def get_permissions(self):
        self.required_permission = PERM_CON_EDIT if self.request.method == "POST" else PERM_CON_VER
        return [IsAuthenticated(), HasDynamicPermission()]

    def get(self, request: Request) -> Response:
        return Response(
            CajaEpic11Service().listar_conceptos(
                request.query_params.get("tipo"), str(request.query_params.get("q") or "")
            )
        )

    def post(self, request: Request) -> Response:
        try:
            data = CajaEpic11Service().crear_concepto(_ctx(request), request.data if isinstance(request.data, dict) else {})
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class ConceptoDetailView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("gastos_frecuentes", "Editar")

    def patch(self, request: Request, pk: int) -> Response:
        try:
            data = CajaEpic11Service().actualizar_concepto(
                _ctx(request), pk, request.data if isinstance(request.data, dict) else {}
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class JornadaAperturaView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = CajaEpic11Service().apertura_jornada(_ctx(request), int(body.get("id_sede") or 0))
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class JornadaBaseInicialView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = CajaEpic11Service().base_inicial_primera(_ctx(request), int(body.get("id_sede") or 0), body.get("monto"))
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class JornadaActualView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_VER

    def get(self, request: Request) -> Response:
        id_sede = int(request.query_params.get("id_sede") or 0)
        try:
            return Response(CajaEpic11Service().jornada_actual(_ctx(request), id_sede))
        except ReglaNegocioError as exc:
            return _err(exc, request)


class GastosAhorrosView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP

    def get(self, request: Request) -> Response:
        id_sede = int(request.query_params.get("id_sede") or 0)
        try:
            return Response(CajaEpic11Service().listar_gastos_ahorros(_ctx(request), id_sede))
        except ReglaNegocioError as exc:
            return _err(exc, request)

    def post(self, request: Request) -> Response:
        try:
            data = CajaEpic11Service().registrar_gasto_o_ahorro(
                _ctx(request), request.data if isinstance(request.data, dict) else {}
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class TransferenciasView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP

    def get(self, request: Request) -> Response:
        id_sede = int(request.query_params.get("id_sede") or 0)
        try:
            return Response(CajaEpic11Service().listar_transferencias(_ctx(request), id_sede))
        except ReglaNegocioError as exc:
            return _err(exc, request)

    def post(self, request: Request) -> Response:
        try:
            data = CajaEpic11Service().registrar_transferencia(
                _ctx(request), request.data if isinstance(request.data, dict) else {}
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class AdicionesView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP

    def post(self, request: Request) -> Response:
        try:
            data = CajaEpic11Service().registrar_adicion(_ctx(request), request.data if isinstance(request.data, dict) else {})
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class EntregasView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP

    def post(self, request: Request) -> Response:
        try:
            data = CajaEpic11Service().registrar_entrega(_ctx(request), request.data if isinstance(request.data, dict) else {})
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data, status=status.HTTP_201_CREATED)


class CorregirMovimientoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP

    def post(self, request: Request, tipo: str, pk: int) -> Response:
        try:
            data = CajaEpic11Service().corregir_movimiento(
                _ctx(request), tipo, pk, request.data if isinstance(request.data, dict) else {}
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class AdjuntosMovimientoView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        return Response(CajaEpic11Service().registrar_adjunto_stub(_ctx(request), body))


class VentaRegistradaView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP

    def patch(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = CajaEpic11Service().actualizar_venta_registrada(
                _ctx(request), int(body.get("id_sede") or 0), body
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class ReporteCuadreView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_VER

    def get(self, request: Request) -> Response:
        try:
            return Response(CajaEpic11Service().cuadre_tiempo_real(_ctx(request), int(request.query_params.get("id_sede") or 0)))
        except ReglaNegocioError as exc:
            return _err(exc, request)


class ReporteCierreView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_OP

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = CajaEpic11Service().cierre_jornada(_ctx(request), int(body.get("id_sede") or 0), body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class ReporteReaperturaView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("cierre_jornada", "Editar")

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            data = CajaEpic11Service().reapertura_jornada(_ctx(request), int(body.get("id_sede") or 0), body)
        except ReglaNegocioError as exc:
            return _err(exc, request)
        return Response(data)


class HistorialJornadasView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = PERM_CIERRE_VER

    def get(self, request: Request) -> Response:
        try:
            return Response(
                CajaEpic11Service().historial(
                    _ctx(request),
                    int(request.query_params.get("id_sede") or 0),
                    request.query_params.get("desde"),
                    request.query_params.get("hasta"),
                )
            )
        except ReglaNegocioError as exc:
            return _err(exc, request)


class HistorialExportView(APIView):
    permission_classes = [IsAuthenticated, HasDynamicPermission]
    required_permission = ("cierre_jornada", "Exportar")

    def get(self, request: Request) -> HttpResponse:
        formato = (request.query_params.get("formato") or "csv").lower()
        try:
            nombre, contenido, mime = CajaEpic11Service().exportar_historial(
                _ctx(request), int(request.query_params.get("id_sede") or 0), formato
            )
        except ReglaNegocioError as exc:
            return Response({"codigo": exc.codigo, "mensaje": exc.mensaje}, status=400)
        resp = HttpResponse(contenido, content_type=mime)
        resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
        return resp
