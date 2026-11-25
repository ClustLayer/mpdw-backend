from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m13_plataforma.observability.interactions_service import registrar_lote
from contratos.dtos import AuthContext


class InteraccionesBatchView(APIView):
    """Lote de clics (público + autenticado). Sin texto libre de formularios."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="analitica_interacciones_batch")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        eventos = body.get("interacciones") or body.get("eventos") or body.get("items") or []
        if not isinstance(eventos, list):
            return Response({"mensaje": "Formato inválido.", "codigo": "PAYLOAD_INVALIDO"}, status=400)
        ctx = getattr(request, "auth_context", None)
        id_usuario = ctx.id_usuario if isinstance(ctx, AuthContext) else None
        resultado = registrar_lote(
            id_usuario=id_usuario,
            eventos=eventos,
            id_correlacion=str(getattr(request, "correlation_id", "") or body.get("id_correlacion") or ""),
        )
        return Response(resultado)