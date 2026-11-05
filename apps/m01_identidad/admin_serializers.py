from rest_framework import serializers


class SedeAsignadaSerializer(serializers.Serializer):
    id_sede = serializers.IntegerField(min_value=1)
    es_principal = serializers.BooleanField()


class CrearUsuarioRequestSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=255)
    apellido = serializers.CharField(max_length=255)
    documento = serializers.CharField(max_length=20)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    email = serializers.EmailField(max_length=255)
    id_rol = serializers.IntegerField(min_value=1)
    sedes = serializers.ListField(child=SedeAsignadaSerializer(), min_length=1)


class EditarUsuarioRequestSerializer(CrearUsuarioRequestSerializer):
    version_fila = serializers.IntegerField(min_value=1)


class CambiarEstadoRequestSerializer(serializers.Serializer):
    accion = serializers.ChoiceField(choices=["activar", "desactivar", "bloquear"])


class PerfilUpdateRequestSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=255)
    apellido = serializers.CharField(max_length=255)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")


class UsuarioListItemSerializer(serializers.Serializer):
    id_usuario = serializers.IntegerField()
    nombre_completo = serializers.CharField()
    documento = serializers.CharField()
    email = serializers.EmailField()
    rol = serializers.CharField()
    estado = serializers.CharField()
    ultimo_acceso = serializers.DateTimeField(allow_null=True)
    sede_principal = serializers.CharField(allow_blank=True)


class UsuarioListResponseSerializer(serializers.Serializer):
    items = UsuarioListItemSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    mensaje = serializers.CharField()


class UsuarioDetalleSerializer(serializers.Serializer):
    id_usuario = serializers.IntegerField()
    nombre = serializers.CharField()
    apellido = serializers.CharField()
    nombre_completo = serializers.CharField()
    documento = serializers.CharField()
    telefono = serializers.CharField()
    email = serializers.EmailField()
    id_rol = serializers.IntegerField()
    rol = serializers.CharField()
    estado = serializers.BooleanField()
    estado_etiqueta = serializers.CharField()
    version_fila = serializers.IntegerField()
    sedes = SedeAsignadaSerializer(many=True)
    acciones_estado = serializers.ListField(child=serializers.CharField())
    puede_contrasena_temporal = serializers.BooleanField()
    mensaje = serializers.CharField(required=False)
