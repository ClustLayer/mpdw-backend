# ==============================================================================
# Serializador de Sedes - MPDW
# SAD Ref: M02, §9.1
# ==============================================================================
from rest_framework import serializers

from apps.m02_sedes.models import Sedes


class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sedes
        fields = ("id_sede", "nombre", "direccion", "telefono", "ciudad", "estado")
        read_only_fields = ("id_sede",)

