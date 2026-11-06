from rest_framework import serializers


class RolListItemSerializer(serializers.Serializer):
    id_rol = serializers.IntegerField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField()
    estado = serializers.BooleanField()
    es_rol_base = serializers.BooleanField()
    version_fila = serializers.IntegerField()


class RolListResponseSerializer(serializers.Serializer):
    items = RolListItemSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    mensaje = serializers.CharField()


class CrearRolRequestSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=30)
    descripcion = serializers.CharField(required=False, allow_blank=True, default="")


class EditarRolRequestSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=30, required=False)
    descripcion = serializers.CharField(required=False, allow_blank=True)
    estado = serializers.BooleanField(required=False)
    version_fila = serializers.IntegerField()


class RolDetalleResponseSerializer(serializers.Serializer):
    id_rol = serializers.IntegerField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField()
    estado = serializers.BooleanField()
    es_rol_base = serializers.BooleanField()
    version_fila = serializers.IntegerField()
    mensaje = serializers.CharField(required=False)


class PermisoListItemSerializer(serializers.Serializer):
    id_permiso = serializers.IntegerField()
    nombre = serializers.CharField()
    modulo = serializers.CharField()
    accion = serializers.CharField()
    descripcion = serializers.CharField()
    estado = serializers.BooleanField()
    version_fila = serializers.IntegerField()


class PermisoListResponseSerializer(serializers.Serializer):
    items = PermisoListItemSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    mensaje = serializers.CharField()


class CrearPermisoRequestSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=100)
    modulo = serializers.CharField(max_length=100)
    accion = serializers.CharField(max_length=50)
    descripcion = serializers.CharField(required=False, allow_blank=True, default="")


class EditarPermisoRequestSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=100, required=False)
    modulo = serializers.CharField(max_length=100, required=False)
    accion = serializers.CharField(max_length=50, required=False)
    descripcion = serializers.CharField(required=False, allow_blank=True)
    estado = serializers.BooleanField(required=False)
    version_fila = serializers.IntegerField()


class CatalogosPermisoResponseSerializer(serializers.Serializer):
    modulos = serializers.ListField(child=serializers.DictField())
    acciones = serializers.ListField(child=serializers.CharField())


class MatrizCambioSerializer(serializers.Serializer):
    id_permiso = serializers.IntegerField()
    permitido = serializers.BooleanField()
    eliminar_excepcion = serializers.BooleanField(required=False, default=False)


class GuardarMatrizRequestSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=["rol", "usuario"])
    id_destino = serializers.IntegerField()
    cambios = MatrizCambioSerializer(many=True)


class AccesosPanelResponseSerializer(serializers.Serializer):
    modulos = serializers.ListField(child=serializers.CharField())
    acciones_por_modulo = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )
