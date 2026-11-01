# ==============================================================================
# Serializadores de Catálogo de Productos - MPDW
# SAD Ref: §9.1, §10.5
# ==============================================================================
from decimal import Decimal

from rest_framework import serializers

from apps.m03_catalogo.models import Productos


class StockInicialInputSerializer(serializers.Serializer):
    """Stock de apertura por sede para el alta de producto."""
    id_sede = serializers.IntegerField(min_value=1)
    cantidad_inicial = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"))


class ProductoCreateSerializer(serializers.Serializer):
    """Validación y sanitización estricta para creación de productos."""
    codigo_producto = serializers.CharField(max_length=50)
    codigo_barras = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    nombre = serializers.CharField(max_length=200)
    descripcion = serializers.CharField(required=False, allow_blank=True, default="")
    precio_venta = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    id_categoria = serializers.IntegerField(min_value=1)
    id_marca = serializers.IntegerField(required=False, allow_null=True)
    id_tipo_producto = serializers.IntegerField(required=False, allow_null=True)
    inventario_habilitado = serializers.BooleanField(default=True)
    stocks_iniciales = StockInicialInputSerializer(many=True, required=False, default=list)


class ProductoUpdatePrecioSerializer(serializers.Serializer):
    """Esquema de entrada para actualización de precio con motivo y versión (TX-06, TX-11)."""
    nuevo_precio = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    motivo = serializers.CharField(min_length=3, max_length=500)
    version = serializers.IntegerField(min_value=1)


class ProductoResponseSerializer(serializers.ModelSerializer):
    """Representación pública y de backoffice del producto (whitelist explícita)."""
    categoria_nombre = serializers.CharField(source="id_categoria.nombre", read_only=True)
    marca_nombre = serializers.CharField(source="id_marca.nombre", read_only=True, default=None)

    class Meta:
        model = Productos
        fields = (
            "id_producto",
            "codigo_producto",
            "codigo_barras",
            "nombre",
            "descripcion",
            "precio_venta",
            "categoria_nombre",
            "marca_nombre",
            "inventario_habilitado",
            "version",
            "estado",
            "fecha_creacion",
        )
        read_only_fields = ("id_producto", "version", "fecha_creacion")

