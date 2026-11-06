from rest_framework import serializers


class UsuarioBitacoraAnidadoSerializer(serializers.Serializer):
    id_usuario = serializers.IntegerField(allow_null=True)
    nombre = serializers.CharField(allow_blank=True)
    email = serializers.CharField(allow_null=True)


class AuditoriaFilaSerializer(serializers.Serializer):
    id_auditoria = serializers.IntegerField()
    fecha_hora = serializers.CharField(allow_null=True)
    usuario = UsuarioBitacoraAnidadoSerializer()
    accion = serializers.CharField()
    entidad = serializers.CharField()
    id_entidad = serializers.IntegerField()
    ip_origen = serializers.CharField()
    resumen = serializers.CharField()
    datos_anteriores = serializers.JSONField(allow_null=True)
    datos_nuevos = serializers.JSONField(allow_null=True)
    motivo = serializers.CharField()
    resultado = serializers.CharField()


class BitacoraListResponseSerializer(serializers.Serializer):
    items = AuditoriaFilaSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    mensaje = serializers.CharField()


class UsuarioOpcionSerializer(serializers.Serializer):
    id_usuario = serializers.IntegerField()
    etiqueta = serializers.CharField()
    email = serializers.EmailField()


class UsuariosBitacoraQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=80)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=30)
