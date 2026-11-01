# ==============================================================================
# Serializadores de Inventario - MPDW
# SAD Ref: M04, §9.1
# ==============================================================================
from rest_framework import serializers

from apps.m04_inventario.models import Inventarios, Movimientos_inventario


class InventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventarios
        fields = ("id_inventario", "id_producto", "id_sede", "cantidad_actual", "cantidad_reservada")
        read_only_fields = ("id_inventario", "cantidad_actual", "cantidad_reservada")


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimientos_inventario
        fields = (
            "id_movimiento",
            "id_inventario",
            "tipo_movimiento",
            "cantidad",
            "cantidad_anterior",
            "cantidad_nueva",
            "motivo",
            "fecha_hora",
        )
        read_only_fields = ("id_movimiento", "fecha_hora")

