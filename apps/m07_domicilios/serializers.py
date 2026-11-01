from rest_framework import serializers

from apps.m07_domicilios.models import Entregas


class EntregaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entregas
        fields = ("id_entrega", "id_factura", "id_mensajero", "direccion_entrega", "estado", "fecha_solicitud")
        read_only_fields = ("id_entrega", "fecha_solicitud")

