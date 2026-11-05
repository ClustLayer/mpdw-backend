# ==============================================================================
# Serializadores de Identidad y Sesión - MPDW
# ==============================================================================
from rest_framework import serializers

from apps.m01_identidad.mensajes import MSG_EMAIL_INVALIDO, MSG_PASSWORD_VACIA
from apps.m01_identidad.models import Usuarios
from apps.m01_identidad.politicas import correo_valido


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255, allow_blank=True, trim_whitespace=True)
    password = serializers.CharField(max_length=128, allow_blank=True, write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict) -> dict:
        email = (attrs.get("email") or "").strip()
        password = attrs.get("password") or ""
        if not correo_valido(email):
            raise serializers.ValidationError({"email": MSG_EMAIL_INVALIDO})
        if password == "":
            raise serializers.ValidationError({"password": MSG_PASSWORD_VACIA})
        attrs["email"] = email
        attrs["password"] = password
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=False, allow_null=True)
    token_type = serializers.CharField(default="Bearer")
    expires_in_minutes = serializers.IntegerField(default=15)
    id_usuario = serializers.IntegerField(required=False)
    email = serializers.CharField(required=False)
    nombre = serializers.CharField(required=False)
    rol = serializers.CharField(required=False)
    sedes_asignadas = serializers.ListField(child=serializers.IntegerField(), required=False)
    mensaje = serializers.CharField(required=False, allow_blank=True)
    debe_cambiar_password = serializers.BooleanField(required=False)
    requiere_2fa = serializers.BooleanField(required=False)
    redireccion = serializers.CharField(required=False)
    desafio_token = serializers.CharField(required=False, allow_null=True)


class MensajeResponseSerializer(serializers.Serializer):
    mensaje = serializers.CharField()


class RecuperarRequestSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)


class RestablecerRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(max_length=64)
    confirmar = serializers.CharField(max_length=64)


class CambiarContrasenaRequestSerializer(serializers.Serializer):
    password_actual = serializers.CharField()
    password = serializers.CharField(max_length=64)
    confirmar = serializers.CharField(max_length=64)


class CambiarContrasenaResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()
    mensaje = serializers.CharField()
    requiere_2fa = serializers.BooleanField()
    redireccion = serializers.CharField()
    desafio_token = serializers.CharField(required=False, allow_null=True)


class Codigo2FARequestSerializer(serializers.Serializer):
    codigo = serializers.CharField(min_length=6, max_length=6)
    desafio_token = serializers.CharField(required=False, allow_blank=True)


class Reenviar2FARequestSerializer(serializers.Serializer):
    desafio_token = serializers.CharField()


class PoliticaSesionSerializer(serializers.Serializer):
    access_minutos = serializers.IntegerField()
    refresh_dias = serializers.IntegerField()
    inactividad_minutos = serializers.IntegerField()
    aviso_minutos = serializers.IntegerField()
    intentos_maximos = serializers.IntegerField()
    bloqueo_minutos = serializers.IntegerField()


class UserProfileSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source="id_rol.nombre", read_only=True)

    class Meta:
        model = Usuarios
        fields = (
            "id_usuario",
            "email",
            "documento",
            "nombre",
            "apellido",
            "telefono",
            "tipo_sangre",
            "fecha_nacimiento",
            "direccion",
            "contacto_emergencia_nombre",
            "contacto_emergencia_telefono",
            "rol_nombre",
            "dosfa_habilitado",
            "debe_cambiar_password",
            "ultimo_acceso",
            "version_fila",
        )
        read_only_fields = (
            "id_usuario",
            "email",
            "documento",
            "rol_nombre",
            "dosfa_habilitado",
            "debe_cambiar_password",
            "ultimo_acceso",
            "version_fila",
        )
