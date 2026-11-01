from rest_framework import serializers

from apps.m12_tienda_publica.models import Pedidos_web


class PedidoWebSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedidos_web
        fields = (
            "id_pedido_web",
            "clave_idempotencia",
            "nombre_contacto",
            "telefono_contacto",
            "id_sede",
            "items_json",
            "total_estimado",
            "estado",
            "fecha_creacion",
        )
        read_only_fields = ("id_pedido_web", "fecha_creacion")

