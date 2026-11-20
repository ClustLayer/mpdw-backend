from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m11_eventos.models import Eventos_novedades
from apps.m11_eventos.serializers import EventoSerializer


class EventoListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        eventos = Eventos_novedades.objects.filter(estado=True).order_by("-fecha_inicio")[:20]
        serializer = EventoSerializer(eventos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

