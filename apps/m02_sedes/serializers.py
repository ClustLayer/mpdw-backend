from rest_framework import serializers


class HorarioSerializer(serializers.Serializer):
    dia_semana = serializers.IntegerField(min_value=1, max_value=7)
    hora_apertura = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    hora_cierre = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cerrado = serializers.BooleanField(required=False, default=False)


class SedePublicSerializer(serializers.Serializer):
    id_sede = serializers.IntegerField()
    nombre = serializers.CharField()
    direccion = serializers.CharField()
    ciudad = serializers.CharField()
    telefono = serializers.CharField()
    whatsapp = serializers.CharField()
    maps_url = serializers.CharField()
    map_query = serializers.CharField()
    orden = serializers.IntegerField()
    es_principal = serializers.BooleanField(required=False)
    horarios = HorarioSerializer(many=True)
    schedule_text = serializers.CharField()


class CrearSedeRequestSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=255)
    direccion = serializers.CharField(max_length=255)
    telefono = serializers.CharField(max_length=20)
    whatsapp = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    ciudad = serializers.CharField(max_length=50, required=False, allow_blank=True, default="Cali")
    maps_url = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    map_query = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    orden = serializers.IntegerField(required=False, default=10)
    es_principal = serializers.BooleanField(required=False, default=False)
    id_usuario_responsable = serializers.IntegerField(required=False, allow_null=True)
    horarios = HorarioSerializer(many=True, required=False)


class EditarSedeRequestSerializer(CrearSedeRequestSerializer):
    estado = serializers.BooleanField(required=False)
    version_fila = serializers.IntegerField(min_value=1)


class ConsolidadoQuerySerializer(serializers.Serializer):
    id_sede = serializers.IntegerField(required=False, allow_null=True)
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
