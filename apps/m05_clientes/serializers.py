from rest_framework import serializers

from apps.m05_clientes.models import Clientes


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clientes
        fields = ("id_cliente", "documento", "nombre", "telefono", "email", "direccion", "estado")
        read_only_fields = ("id_cliente",)

