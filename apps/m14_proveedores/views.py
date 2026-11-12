from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m14_proveedores.models import Proveedores
from apps.m14_proveedores.serializers import ProveedorSerializer


class ProveedorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        proveedores = Proveedores.objects.filter(estado=True).order_by("nombre")[:50]
        serializer = ProveedorSerializer(proveedores, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
