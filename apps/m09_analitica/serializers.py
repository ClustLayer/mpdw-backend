from rest_framework import serializers


class DashboardVentasSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    total_ventas = serializers.DecimalField(max_digits=14, decimal_places=2)
    cantidad_facturas = serializers.IntegerField()

