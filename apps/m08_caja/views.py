from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m08_caja.models import Reportes_diarios
from apps.m08_caja.serializers import ReporteDiarioSerializer


class ReporteDiarioListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reportes = Reportes_diarios.objects.all().order_by("-fecha")[:30]
        serializer = ReporteDiarioSerializer(reportes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

