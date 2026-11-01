from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m07_domicilios.models import Entregas
from apps.m07_domicilios.serializers import EntregaSerializer


class EntregaListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entregas = Entregas.objects.filter(estado="PENDIENTE")
        serializer = EntregaSerializer(entregas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

