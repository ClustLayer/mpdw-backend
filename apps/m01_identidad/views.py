# ==============================================================================
# Vistas de Autenticación - MPDW (Epica 1)
# ==============================================================================
import logging
from typing import Literal

from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m01_identidad.admin_serializers import PerfilUpdateRequestSerializer
from apps.m01_identidad.mensajes import (
    MSG_2FA_ERROR,
    MSG_CAMBIO_ERROR,
    MSG_EMAIL_INVALIDO,
    MSG_ERROR_LOGIN,
    MSG_ERROR_SOLICITUD,
    MSG_RENOVAR_ERROR,
    MSG_RESET_INVALIDO,
    MSG_SESION_CONTINUA,
    MSG_SESION_EXPIRADA,
)
from apps.m01_identidad.politicas import correo_valido
from apps.m01_identidad.serializers import (
    CambiarContrasenaRequestSerializer,
    CambiarContrasenaResponseSerializer,
    Codigo2FARequestSerializer,
    LoginRequestSerializer,
    MensajeResponseSerializer,
    PoliticaSesionSerializer,
    RecuperarRequestSerializer,
    Reenviar2FARequestSerializer,
    RestablecerRequestSerializer,
    TokenResponseSerializer,
    UserProfileSerializer,
)
from apps.m01_identidad.services import (
    AuthService,
    ContrasenaService,
    RecuperacionService,
    Verificacion2FAService,
)
from apps.m10_auditoria.services import AuditService
from contratos.excepciones import AutenticacionError, DominioError, ReglaNegocioError

logger = logging.getLogger(__name__)


def _correo():
    from apps.m13_plataforma.adapters.correo_factory import construir_adaptador_correo

    return construir_adaptador_correo()


def _auth() -> AuthService:
    return AuthService(audit_port=AuditService(), email_port=_correo())


def _ip(request: Request) -> str:
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def _ua(request: Request) -> str:
    return request.META.get("HTTP_USER_AGENT", "Unknown")


def _cid(request: Request) -> str:
    return getattr(request, "correlation_id", "")


def _error(codigo: str, mensaje: str, http_status: int, request: Request) -> Response:
    return Response(
        {"codigo": codigo, "mensaje": mensaje, "detalles": [], "idCorrelacion": _cid(request)},
        status=http_status,
    )


def _primer_mensaje(errores: object) -> str:
    if isinstance(errores, dict):
        for valor in errores.values():
            return _primer_mensaje(valor)
    if isinstance(errores, list) and errores:
        return _primer_mensaje(errores[0])
    return str(errores)


def _samesite() -> Literal["Lax", "None"]:
    if settings.DEBUG:
        return "Lax"
    return "None"


def _poner_refresh(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        max_age=int(settings.REFRESH_TOKEN_LIFETIME_DAYS) * 86400,
        httponly=True,
        secure=not settings.DEBUG,
        samesite=_samesite(),
        path="/api/v1/auth",
    )


def _quitar_refresh(response: Response) -> None:
    response.delete_cookie("refresh_token", path="/api/v1/auth", samesite=_samesite())


def _refresh_entrante(request: Request) -> str | None:
    cuerpo = request.data.get("refresh_token") if isinstance(request.data, dict) else None
    return request.COOKIES.get("refresh_token") or cuerpo


def _origen_confiable(request: Request) -> bool:
    """Valida Origin/Referer para operaciones con cookie refresh (CSRF)."""
    origen = (request.headers.get("Origin") or "").strip()
    referer = (request.headers.get("Referer") or "").strip()
    candidato = origen or referer
    if not candidato:
        return True
    permitidos = {settings.FRONTEND_URL.rstrip("/")}
    permitidos.update(o.rstrip("/") for o in getattr(settings, "CORS_ALLOWED_ORIGINS", []) if o)
    return any(candidato.startswith(base) for base in permitidos)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "auth"

    @extend_schema(
        summary="Inicio de sesion",
        description="Autentica usuario y emite JWT corto y cookie HttpOnly con refresh token.",
        request=LoginRequestSerializer,
        responses={200: TokenResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = LoginRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _error("DATOS_INVALIDOS", _primer_mensaje(serializer.errors), status.HTTP_400_BAD_REQUEST, request)
        try:
            resultado = _auth().autenticar(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                ip=_ip(request),
                user_agent=_ua(request),
                id_correlacion=_cid(request),
            )
        except AutenticacionError:
            raise
        except Exception:
            logger.exception("Fallo no anticipado al iniciar sesion")
            return _error("ERROR_LOGIN", MSG_ERROR_LOGIN, status.HTTP_500_INTERNAL_SERVER_ERROR, request)

        ctx = resultado.ctx
        cuerpo = {
            "token_type": "Bearer",
            "expires_in_minutes": int(settings.ACCESS_TOKEN_LIFETIME_MINUTES),
            "mensaje": resultado.mensaje,
            "nombre": resultado.nombre,
            "debe_cambiar_password": resultado.debe_cambiar_password,
            "requiere_2fa": resultado.requiere_2fa,
            "redireccion": resultado.redireccion,
        }
        if resultado.access_token:
            cuerpo["access_token"] = resultado.access_token
        if resultado.desafio_token:
            cuerpo["desafio_token"] = resultado.desafio_token
        if ctx is not None:
            cuerpo.update(
                {
                    "id_usuario": ctx.id_usuario,
                    "email": ctx.email,
                    "rol": ctx.rol_nombre,
                    "sedes_asignadas": list(ctx.sedes_asignadas),
                }
            )
        response = Response(cuerpo, status=status.HTTP_200_OK)
        if resultado.refresh_token:
            _poner_refresh(response, resultado.refresh_token)
        return response


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Continuar sesion",
        request=inline_serializer("RefreshRequest", fields={"refresh_token": serializers.CharField(required=False)}),
        responses={200: inline_serializer("RefreshResponse", fields={"access_token": serializers.CharField(), "token_type": serializers.CharField(), "mensaje": serializers.CharField()})},
    )
    def post(self, request: Request) -> Response:
        if not _origen_confiable(request):
            return _error("ORIGEN_NO_PERMITIDO", "Origen no autorizado para renovar la sesión.", status.HTTP_403_FORBIDDEN, request)
        refresh = _refresh_entrante(request)
        if not refresh:
            return _error("SESION_EXPIRADA", MSG_SESION_EXPIRADA, status.HTTP_401_UNAUTHORIZED, request)
        try:
            acceso, nuevo = _auth().rotar_refresh_token(refresh, ip=_ip(request), id_correlacion=_cid(request))
        except AutenticacionError:
            raise
        except Exception:
            logger.exception("Fallo no anticipado al renovar la sesion")
            return _error("ERROR_RENOVACION", MSG_RENOVAR_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        response = Response(
            {"access_token": acceso, "token_type": "Bearer", "mensaje": MSG_SESION_CONTINUA},
            status=status.HTTP_200_OK,
        )
        _poner_refresh(response, nuevo)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Cierre de sesion",
        description="Revocacion de la familia de refresh tokens y borrado de cookie (ADR-006).",
        request=inline_serializer("LogoutRequest", fields={"refresh_token": serializers.CharField(required=False)}),
        responses={200: MensajeResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        if not _origen_confiable(request):
            return _error("ORIGEN_NO_PERMITIDO", "Origen no autorizado para cerrar la sesión.", status.HTTP_403_FORBIDDEN, request)
        refresh = _refresh_entrante(request)
        if not refresh:
            response = _error("SESION_EXPIRADA", MSG_SESION_EXPIRADA, status.HTTP_401_UNAUTHORIZED, request)
            _quitar_refresh(response)
            return response
        try:
            mensaje = _auth().cerrar_sesion(refresh)
        except AutenticacionError:
            raise
        except DominioError as exc:
            return _error(exc.codigo, exc.mensaje, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        except Exception:
            logger.exception("Fallo no anticipado al cerrar sesion")
            return _error("LOGOUT_FALLO", "No fue posible cerrar la sesión en el servidor. Intente nuevamente.", 500, request)
        response = Response({"mensaje": mensaje}, status=status.HTTP_200_OK)
        _quitar_refresh(response)
        return response


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Perfil de usuario",
        description="Retorna el perfil del usuario autenticado segun JWT.",
        responses={200: UserProfileSerializer},
    )
    def get(self, request: Request) -> Response:
        return Response(UserProfileSerializer(request.user).data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="auth_profile_update",
        summary="Actualizar perfil propio (HU 12)",
        request=PerfilUpdateRequestSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request: Request) -> Response:
        from apps.m01_identidad.admin_usuarios_service import PerfilPropioService
        from apps.m01_identidad.admin_views import _ctx, _dominio

        serializer = PerfilUpdateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _dominio(ReglaNegocioError(str(serializer.errors), codigo="DATOS_INVALIDOS"), request)
        from apps.m01_identidad.models import Usuarios

        if not isinstance(request.user, Usuarios):
            return _error("NO_AUTORIZADO", "Usuario no autenticado.", status.HTTP_401_UNAUTHORIZED, request)
        try:
            mensaje = PerfilPropioService(audit_port=AuditService()).actualizar(
                _ctx(request), request.user, serializer.validated_data
            )
        except (ReglaNegocioError, DominioError) as exc:
            return _dominio(exc, request)
        usuario = Usuarios.objects.select_related("id_rol").get(pk=request.user.pk)
        return Response(
            {"mensaje": mensaje, **UserProfileSerializer(usuario).data},
            status=status.HTTP_200_OK,
        )


class PoliticaSesionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Politica publica de vigencia de sesion", responses={200: PoliticaSesionSerializer})
    def get(self, request: Request) -> Response:
        return Response(
            {
                "access_minutos": int(settings.ACCESS_TOKEN_LIFETIME_MINUTES),
                "refresh_dias": int(settings.REFRESH_TOKEN_LIFETIME_DAYS),
                "inactividad_minutos": int(settings.INACTIVITY_TIMEOUT_MINUTES),
                "aviso_minutos": int(settings.SESSION_WARNING_MINUTES),
                "intentos_maximos": int(settings.MAX_INTENTOS_FALLIDOS),
                "bloqueo_minutos": int(settings.BLOQUEO_MINUTOS),
            },
            status=status.HTTP_200_OK,
        )


class RecuperacionSolicitudView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(summary="Solicitar enlace de recuperacion", request=RecuperarRequestSerializer, responses={200: MensajeResponseSerializer})
    def post(self, request: Request) -> Response:
        email = ""
        if isinstance(request.data, dict):
            email = str(request.data.get("email") or "").strip()
        if not correo_valido(email):
            return _error("DATOS_INVALIDOS", MSG_EMAIL_INVALIDO, status.HTTP_400_BAD_REQUEST, request)
        try:
            mensaje = RecuperacionService(email_port=_correo()).solicitar(email)
        except DominioError as exc:
            return _error(exc.codigo, exc.mensaje, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        except Exception:
            logger.exception("Fallo no anticipado al solicitar recuperacion")
            return _error("ERROR_RECUPERACION", MSG_ERROR_SOLICITUD, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        return Response({"mensaje": mensaje}, status=status.HTTP_200_OK)


class RecuperacionConfirmarView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Restablecer contraseña con enlace de un solo uso",
        request=RestablecerRequestSerializer,
        responses={200: MensajeResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        try:
            mensaje = RecuperacionService().restablecer(
                token=str(data.get("token") or ""),
                nueva=str(data.get("password") or ""),
                confirmar=str(data.get("confirmar") or ""),
            )
        except ReglaNegocioError:
            raise
        except Exception:
            logger.exception("Fallo no anticipado al restablecer contraseña")
            return _error("ERROR_RECUPERACION", MSG_ERROR_SOLICITUD, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        return Response({"mensaje": mensaje}, status=status.HTTP_200_OK)


class CambiarContrasenaView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cambiar contraseña autenticado",
        request=CambiarContrasenaRequestSerializer,
        responses={200: CambiarContrasenaResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        payload = getattr(request, "jwt_payload", {})
        try:
            acceso, mensaje, sigue_2fa, desafio = ContrasenaService(auth=_auth(), audit_port=AuditService()).cambiar(
                usuario=request.user,
                actual=str(data.get("password_actual") or ""),
                nueva=str(data.get("password") or ""),
                confirmar=str(data.get("confirmar") or ""),
                id_sesion=int(payload.get("sid") or 0),
                mfa_pendiente=bool(payload.get("mfa_pendiente")),
                ip=_ip(request),
                user_agent=_ua(request),
                id_correlacion=_cid(request),
            )
        except ReglaNegocioError:
            raise
        except Exception:
            logger.exception("Fallo no anticipado al cambiar contraseña")
            return _error("ERROR_CAMBIO", MSG_CAMBIO_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        redireccion = "verificacion-2fa" if sigue_2fa else "inicio"
        cuerpo = {
            "access_token": acceso,
            "token_type": "Bearer",
            "mensaje": mensaje,
            "requiere_2fa": sigue_2fa,
            "redireccion": redireccion,
        }
        if desafio:
            cuerpo["desafio_token"] = desafio
        return Response(cuerpo, status=status.HTTP_200_OK)


class Verificar2FAView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verificar codigo de segundo factor",
        request=Codigo2FARequestSerializer,
        responses={200: TokenResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        usuario = request.user if getattr(request.user, "is_authenticated", False) else None
        payload = getattr(request, "jwt_payload", {}) if usuario else {}
        sid = payload.get("sid")
        id_sesion = int(sid) if sid else None
        try:
            resultado = Verificacion2FAService(auth=_auth(), email_port=_correo()).verificar(
                usuario=usuario,
                desafio_token=str(data.get("desafio_token") or ""),
                codigo=str(data.get("codigo") or ""),
                id_sesion=id_sesion,
                ip=_ip(request),
                user_agent=_ua(request),
                id_correlacion=_cid(request),
            )
        except (ReglaNegocioError, AutenticacionError):
            raise
        except DominioError as exc:
            return _error(exc.codigo, exc.mensaje, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        except Exception:
            logger.exception("Fallo no anticipado al verificar 2FA")
            return _error("ERROR_2FA", MSG_2FA_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        cuerpo = {
            "mensaje": resultado.mensaje,
            "nombre": resultado.nombre,
            "redireccion": resultado.redireccion,
            "debe_cambiar_password": resultado.debe_cambiar_password,
            "requiere_2fa": False,
            "token_type": "Bearer",
        }
        if resultado.access_token:
            cuerpo["access_token"] = resultado.access_token
        response = Response(cuerpo, status=status.HTTP_200_OK)
        if resultado.refresh_token:
            _poner_refresh(response, resultado.refresh_token)
        return response


class Reenviar2FAView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Reenviar codigo de segundo factor",
        request=Reenviar2FARequestSerializer,
        responses={200: inline_serializer("Reenviar2FAResponse", fields={"mensaje": serializers.CharField(), "desafio_token": serializers.CharField()})},
    )
    def post(self, request: Request) -> Response:
        serializer = Reenviar2FARequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _error("DATOS_INVALIDOS", _primer_mensaje(serializer.errors), status.HTTP_400_BAD_REQUEST, request)
        usuario = request.user if getattr(request.user, "is_authenticated", False) else None
        try:
            mensaje, desafio = Verificacion2FAService(auth=_auth(), email_port=_correo()).reenviar(
                usuario=usuario,
                desafio_token=str(serializer.validated_data["desafio_token"]),
            )
        except (ReglaNegocioError, AutenticacionError):
            raise
        except DominioError as exc:
            return _error(exc.codigo, exc.mensaje, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        except Exception:
            logger.exception("Fallo no anticipado al reenviar 2FA")
            return _error("ERROR_2FA", MSG_2FA_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR, request)
        return Response({"mensaje": mensaje, "desafio_token": desafio}, status=status.HTTP_200_OK)


class ContratoAuthView(APIView):
    """Contrato legible para el frontend. No expone secretos."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(summary="Contrato de autenticacion para el frontend", responses={200: inline_serializer("ContratoAuth", fields={"endpoints": serializers.DictField(), "mensajes": serializers.DictField()})})
    def get(self, request: Request) -> Response:
        return Response(
            {
                "endpoints": {
                    "login": {"method": "POST", "path": "/api/v1/auth/login"},
                    "refresh": {"method": "POST", "path": "/api/v1/auth/refresh"},
                    "logout": {"method": "POST", "path": "/api/v1/auth/logout"},
                    "recuperar": {"method": "POST", "path": "/api/v1/auth/recuperar"},
                    "restablecer": {"method": "POST", "path": "/api/v1/auth/restablecer"},
                    "cambiar_contrasena": {"method": "POST", "path": "/api/v1/auth/cambiar-contrasena"},
                    "verificar_2fa": {"method": "POST", "path": "/api/v1/auth/verificar-2fa"},
                    "reenviar_2fa": {"method": "POST", "path": "/api/v1/auth/reenviar-2fa"},
                    "politica_sesion": {"method": "GET", "path": "/api/v1/auth/politica-sesion"},
                },
                "mensajes": {
                    "credenciales": "Credenciales no válidas, por favor intente de nuevo.",
                    "bloqueado": "Acceso temporalmente bloqueado. Intente más tarde o contacte al administrador.",
                    "logout": "Sesión cerrada correctamente.",
                    "sesion_expirada": MSG_SESION_EXPIRADA,
                    "inactividad": "Su sesión expiró por inactividad. Inicie sesión nuevamente.",
                    "recuperacion": "Si el correo está registrado, recibirá un enlace para restablecer su contraseña.",
                    "reset_invalido": MSG_RESET_INVALIDO,
                },
            },
            status=status.HTTP_200_OK,
        )
