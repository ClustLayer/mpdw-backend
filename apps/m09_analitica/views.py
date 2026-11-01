from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m09_analitica.serializers import DashboardVentasSerializer
from apps.m09_analitica.services import AnaliticaService


class DashboardVentasView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = AnaliticaService()

    def get(self, request):
        datos = self._service.obtener_ventas()
        serializer = DashboardVentasSerializer(datos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

