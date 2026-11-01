# ==============================================================================
# Vistas de Autenticación y Perfil - MPDW
# SAD Ref: §9.1, I-03, ADR-006, §10.3
# ==============================================================================
from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.serializers import (
    LoginRequestSerializer,
    TokenResponseSerializer,
    UserProfileSerializer,
)
from apps.m01_identidad.services import AuthService
from apps.m10_auditoria.services import AuditService


class LoginView(APIView):
    """Inicio de sesión con emisión de JWT corto y refresh token opaco en cookie HttpOnly."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "auth"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auth_service = AuthService(audit_port=AuditService())

    @extend_schema(
        summary="Inicio de sesion",
        description="Autentica usuario y emite JWT corto y cookie HttpOnly con refresh token.",
        request=LoginRequestSerializer,
        responses={200: TokenResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
        correlation_id = getattr(request, "correlation_id", "")

        access_token, refresh_token, ctx = self._auth_service.autenticar(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            ip=ip,
            user_agent=user_agent,
            id_correlacion=correlation_id,
        )

        response_data = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in_minutes": getattr(settings, "ACCESS_TOKEN_LIFETIME_MINUTES", 15),
            "id_usuario": ctx.id_usuario,
            "email": ctx.email,
            "rol": ctx.rol_nombre,
            "sedes_asignadas": list(ctx.sedes_asignadas),
        }

        response = Response(response_data, status=status.HTTP_200_OK)

        # Enviar refresh token en cookie segura HttpOnly (ADR-006)
        max_age = getattr(settings, "REFRESH_TOKEN_LIFETIME_DAYS", 7) * 86400
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=max_age,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Strict",
            path="/api/v1/auth",
        )
        return response


class TokenRefreshView(APIView):
    """Rotación de refresh token y renovación de access token (ADR-006)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auth_service = AuthService(audit_port=AuditService())

    @extend_schema(
        summary="Refresco de token de acceso",
        description="Rotacion opaca de refresh token (cookie HttpOnly o body) (ADR-006).",
        request=inline_serializer("RefreshRequest", fields={"refresh_token": serializers.CharField(required=False)}),
        responses={200: inline_serializer("RefreshResponse", fields={"access_token": serializers.CharField(), "token_type": serializers.CharField()})},
    )
    def post(self, request: Request) -> Response:
        token_payload = request.data.get("refresh_token") if isinstance(request.data, dict) else None
        refresh_token = request.COOKIES.get("refresh_token") or token_payload
        if not refresh_token:
            return Response(
                {"codigo": "REFRESH_TOKEN_REQUERIDO", "mensaje": "Token de refresco ausente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
        correlation_id = getattr(request, "correlation_id", "")

        nuevo_access, nuevo_refresh = self._auth_service.rotar_refresh_token(
            refresh_token=refresh_token,
            ip=ip,
            id_correlacion=correlation_id,
        )

        response = Response({"access_token": nuevo_access, "token_type": "Bearer"}, status=status.HTTP_200_OK)

        max_age = getattr(settings, "REFRESH_TOKEN_LIFETIME_DAYS", 7) * 86400
        response.set_cookie(
            key="refresh_token",
            value=nuevo_refresh,
            max_age=max_age,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Strict",
            path="/api/v1/auth",
        )
        return response


class LogoutView(APIView):
    """Cierre de sesión con revocación de familia y eliminación de cookie."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auth_service = AuthService()

    @extend_schema(
        summary="Cierre de sesion",
        description="Revocacion de la familia de refresh tokens y borrado de cookie (ADR-006).",
        request=inline_serializer("LogoutRequest", fields={"refresh_token": serializers.CharField(required=False)}),
        responses={200: inline_serializer("LogoutResponse", fields={"mensaje": serializers.CharField()})},
    )
    def post(self, request: Request) -> Response:
        token_payload = request.data.get("refresh_token") if isinstance(request.data, dict) else None
        refresh_token = request.COOKIES.get("refresh_token") or token_payload
        if refresh_token:
            self._auth_service.cerrar_sesion(refresh_token)

        response = Response({"mensaje": "Sesion cerrada exitosamente."}, status=status.HTTP_200_OK)
        response.delete_cookie("refresh_token", path="/api/v1/auth")
        return response


class ProfileView(APIView):
    """Consulta de perfil de usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Perfil de usuario",
        description="Retorna el perfil del usuario autenticado segun JWT.",
        responses={200: UserProfileSerializer},
    )
    def get(self, request: Request) -> Response:
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

