# ==============================================================================
# Serializadores de Identidad y Sesión - MPDW
# SAD Ref: §9.1, §10.5
# ==============================================================================
from rest_framework import serializers

from apps.m01_identidad.models import Usuarios


class LoginRequestSerializer(serializers.Serializer):
    """Esquema de entrada para solicitud de inicio de sesión."""
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    """Respuesta con token de acceso JWT y metadatos de usuario."""
    access_token = serializers.CharField()
    token_type = serializers.CharField(default="Bearer")
    expires_in_minutes = serializers.IntegerField(default=15)
    id_usuario = serializers.IntegerField()
    email = serializers.CharField()
    rol = serializers.CharField()
    sedes_asignadas = serializers.ListField(child=serializers.IntegerField())


class UserProfileSerializer(serializers.ModelSerializer):
    """Perfil del usuario autenticado (whitelist explícita)."""
    rol_nombre = serializers.CharField(source="id_rol.nombre", read_only=True)

    class Meta:
        model = Usuarios
        fields = ("id_usuario", "email", "documento", "nombre", "rol_nombre", "dosfa_habilitado")
        read_only_fields = ("id_usuario", "email", "documento", "rol_nombre")

