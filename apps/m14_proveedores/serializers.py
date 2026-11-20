from rest_framework import serializers

from apps.m14_proveedores.models import Proveedores


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedores
        fields = (
            "id_proveedor",
            "nombre",
            "tipo_documento",
            "numero_documento",
            "telefono",
            "correo",
            "ciudad",
            "estado",
        )
        read_only_fields = ("id_proveedor",)
