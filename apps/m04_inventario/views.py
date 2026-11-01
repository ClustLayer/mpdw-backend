# ==============================================================================
# Vistas de Inventario - MPDW
# SAD Ref: M04, §9.1
# ==============================================================================
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m04_inventario.models import Inventarios
from apps.m04_inventario.serializers import InventarioSerializer


class InventarioListView(APIView):
    """Consulta de existencias por producto y sede."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Consulta de existencias",
        description="Filtra existencias de inventario por producto y/o sede.",
        parameters=[
            OpenApiParameter("producto", int, description="ID del producto", required=False),
            OpenApiParameter("sede", int, description="ID de la sede", required=False),
        ],
        responses={200: InventarioSerializer(many=True)},
    )
    def get(self, request):
        id_producto = request.query_params.get("producto")
        id_sede = request.query_params.get("sede")

        qs = Inventarios.objects.all()
        if id_producto:
            qs = qs.filter(id_producto_id=id_producto)
        if id_sede:
            qs = qs.filter(id_sede_id=id_sede)

        serializer = InventarioSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

