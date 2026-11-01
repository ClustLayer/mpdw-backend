from rest_framework import serializers

from apps.m06_ventas.models import Facturas


class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facturas
        fields = ("id_factura", "id_sede", "serie", "numero_factura", "total", "estado", "fecha_hora")
        read_only_fields = ("id_factura", "fecha_hora")

