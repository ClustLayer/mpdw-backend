# ==============================================================================
# Clase de Autenticación JWT para DRF - MPDW
# SAD Ref: ADR-006, §10.3
# ==============================================================================
from typing import Any

import jwt
from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from apps.m01_identidad.models import Usuario_sede, Usuarios
from contratos.dtos import AuthContext


class JWTAuthentication(BaseAuthentication):
    """Autentica peticiones mediante token de acceso Bearer JWT de corta duración."""

    def authenticate(self, request) -> tuple[Usuarios, AuthContext] | None:
        auth_header = get_authorization_header(request).split()
        if not auth_header or auth_header[0].lower() != b"bearer":
            return None

        if len(auth_header) == 1:
            raise AuthenticationFailed("Token de autorizacion ausente en la cabecera Bearer.")
        elif len(auth_header) > 2:
            raise AuthenticationFailed("Formato de cabecera de autorizacion invalido.")

        token = auth_header[1].decode("utf-8")

        try:
            signing_key = getattr(settings, "JWT_SIGNING_KEY", "secret")
            payload: dict[str, Any] = jwt.decode(token, signing_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as err:
            raise AuthenticationFailed("El token de acceso ha expirado.") from err
        except jwt.PyJWTError as err:
            raise AuthenticationFailed("Token de acceso invalido.") from err

        user_id = payload.get("sub")
        if payload.get("typ") == "2fa":
            raise AuthenticationFailed("El desafio de verificacion no autoriza el acceso.")

        if not user_id:
            raise AuthenticationFailed("Token de acceso sin identificador de usuario.")

        try:
            user = Usuarios.objects.select_related("id_rol").get(pk=int(user_id))
        except (Usuarios.DoesNotExist, ValueError) as err:
            raise AuthenticationFailed("El usuario del token no existe.") from err

        if not user.estado or user.esta_bloqueado:
            raise AuthenticationFailed("Usuario inactivo o bloqueado.")

        token_cv = payload.get("cv")
        user_cv = int(getattr(user, "credential_version", 1) or 1)
        if token_cv is not None and int(token_cv) != user_cv:
            raise AuthenticationFailed("El token de acceso fue revocado.")

        sedes = tuple(
            Usuario_sede.objects.filter(id_usuario=user, estado=True).values_list(
                "id_sede_id", flat=True
            )
        )
        es_global = user.id_rol.nombre == "Administrador"

        correlation_id = getattr(request, "correlation_id", "")
        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")

        self._exigir_paso_pendiente(request, payload)

        auth_context = AuthContext(
            id_usuario=user.id_usuario,
            email=user.email,
            rol_nombre=user.id_rol.nombre,
            sedes_asignadas=sedes,
            es_global=es_global,
            ip=ip,
            user_agent=user_agent,
            id_correlacion=correlation_id,
        )

        request.auth_context = auth_context
        request.jwt_payload = payload
        return (user, auth_context)

    def _exigir_paso_pendiente(self, request, payload: dict[str, Any]) -> None:
        ruta = request.path.rstrip("/")
        cambio = {
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",
            "/api/v1/auth/profile",
            "/api/v1/auth/cambiar-contrasena",
            "/api/v1/auth/politica-sesion",
        }
        doble_factor = cambio | {
            "/api/v1/auth/verificar-2fa",
            "/api/v1/auth/reenviar-2fa",
        }
        if payload.get("mcp") and ruta not in cambio:
            raise AuthenticationFailed("Debe cambiar su contraseña antes de continuar.")
        if payload.get("mfa_pendiente") and not payload.get("mcp") and ruta not in doble_factor:
            raise AuthenticationFailed("Debe completar la verificación en dos pasos.")


class JWTAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = "apps.m01_identidad.authentication.JWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
