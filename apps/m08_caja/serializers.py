from rest_framework import serializers

from apps.m08_caja.models import Reportes_diarios


class ReporteDiarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reportes_diarios
        fields = ("id_reporte_diario", "id_sede", "fecha", "base_inicial", "estado", "fecha_apertura")
        read_only_fields = ("id_reporte_diario", "fecha_apertura")

