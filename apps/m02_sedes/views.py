# ==============================================================================
# Vistas de Sedes - MPDW
# SAD Ref: M02, §9.1
# ==============================================================================
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m02_sedes.serializers import SedeSerializer
from apps.m02_sedes.services import SedeService


class SedeListView(APIView):
    """Listado público de sedes activas."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = SedeService()

    @extend_schema(
        summary="Listado de sedes",
        description="Consulta pública de sedes habilitadas.",
        responses={200: SedeSerializer(many=True)},
    )
    def get(self, request):
        sedes = self._service.listar_sedes()
        serializer = SedeSerializer(sedes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

