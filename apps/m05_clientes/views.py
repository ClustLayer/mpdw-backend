from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m05_clientes.models import Clientes
from apps.m05_clientes.serializers import ClienteSerializer


class ClienteListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        clientes = Clientes.objects.filter(estado=True)
        serializer = ClienteSerializer(clientes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

