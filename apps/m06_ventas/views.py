from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m06_ventas.models import Facturas
from apps.m06_ventas.serializers import FacturaSerializer


class FacturaListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        facturas = Facturas.objects.all().order_by("-fecha_hora")[:50]
        serializer = FacturaSerializer(facturas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

