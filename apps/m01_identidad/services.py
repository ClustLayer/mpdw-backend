# ==============================================================================
# Servicios de Autenticación y Autorización - MPDW
# SAD Ref: M01, ADR-006, ADR-007, §10.3, §10.4, BR-08, BR-09, BR-10
# ==============================================================================
import secrets
import time
import uuid
from datetime import timedelta
from typing import Any

import jwt
from django.conf import settings
from django.utils import timezone

from apps.m01_identidad.repositories import (
    PermissionRepository,
    SessionRepository,
    UserRepository,
)
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import AutenticacionError
from contratos.puertos.auditoria import AuditPort


class AuthService:
    """Casos de uso de inicio de sesión, renovación con rotación opaca y logout."""

    def __init__(
        self,
        user_repo: UserRepository | None = None,
        session_repo: SessionRepository | None = None,
        audit_port: AuditPort | None = None,
    ) -> None:
        self._users = user_repo or UserRepository()
        self._sessions = session_repo or SessionRepository()
        self._audit = audit_port

    def autenticar(
        self,
        email: str,
        password: str,
        ip: str = "127.0.0.1",
        user_agent: str = "Unknown",
        id_correlacion: str = "",
    ) -> tuple[str, str, AuthContext]:
        """Autentica credenciales y emite access JWT corto y refresh token opaco con familia."""
        usuario = self._users.buscar_por_email(email)

        # Validación genérica para mitigar enumeración (SAD §10.3)
        if not usuario or not usuario.estado or usuario.esta_bloqueado or not usuario.check_password(password):
            if usuario and usuario.estado:
                self._users.incrementar_intentos_fallidos(usuario)
            raise AutenticacionError("Credenciales invalidas o cuenta no autorizada.")

        self._users.restablecer_intentos_fallidos(usuario)

        # Generar tokens
        id_familia = uuid.uuid4()
        refresh_token = secrets.token_urlsafe(48)
        duracion_dias = getattr(settings, "REFRESH_TOKEN_LIFETIME_DAYS", 7)
        sesion = self._sessions.registrar_sesion(
            usuario=usuario,
            refresh_token=refresh_token,
            id_familia=id_familia,
            duracion_dias=duracion_dias,
            ip=ip,
        )

        sedes = self._users.obtener_sedes_asignadas_ids(usuario.id_usuario)
        es_global = usuario.id_rol.nombre == "Administrador"

        ctx = AuthContext(
            id_usuario=usuario.id_usuario,
            email=usuario.email,
            rol_nombre=usuario.id_rol.nombre,
            sedes_asignadas=sedes,
            es_global=es_global,
            ip=ip,
            user_agent=user_agent,
            id_correlacion=id_correlacion,
        )

        access_token = self._generar_jwt_access(usuario, sesion.id_sesion)

        if self._audit:
            self._audit.registrar(
                AuditoriaDTO(
                    id_usuario=usuario.id_usuario,
                    accion="LOGIN_EXITOSO",
                    entidad="Usuarios",
                    id_entidad=usuario.id_usuario,
                    datos_antes=None,
                    datos_despues={"email": usuario.email, "id_familia": str(id_familia)},
                    motivo="Inicio de sesion exitoso",
                    id_correlacion=id_correlacion,
                    ip=ip,
                    user_agent=user_agent,
                )
            )

        return access_token, refresh_token, ctx

    def rotar_refresh_token(
        self,
        refresh_token: str,
        ip: str = "127.0.0.1",
        id_correlacion: str = "",
    ) -> tuple[str, str]:
        """Rotación de refresh token con detección estricta de reuso (ADR-006)."""
        sesion = self._sessions.buscar_por_token(refresh_token)

        if not sesion:
            raise AutenticacionError("Token de sesion invalido o revocado.")

        # Detección de reuso: si ya fue reemplazada o revocada, revocar toda la familia
        if sesion.revocada or sesion.reemplazada_por:
            self._sessions.revocar_familia(sesion.id_familia)
            if self._audit:
                self._audit.registrar(
                    AuditoriaDTO(
                        id_usuario=sesion.id_usuario_id,
                        accion="ALERTA_REUSO_TOKEN",
                        entidad="Sesiones_usuario",
                        id_entidad=sesion.id_sesion,
                        datos_antes={"id_familia": str(sesion.id_familia)},
                        datos_despues=None,
                        motivo="Reuso de token detectado. Familia de sesiones revocada.",
                        resultado="RECHAZADO",
                        id_correlacion=id_correlacion,
                        ip=ip,
                    )
                )
            raise AutenticacionError("Sesion revocada por deteccion de reutilizacion.")

        # Verificar expiración absoluta e inactividad deslizante (SAD AD-11)
        ahora = timezone.now()
        if ahora > sesion.fecha_expiracion_absoluta:
            self._sessions.revocar_familia(sesion.id_familia)
            raise AutenticacionError("La sesion ha expirado.")

        minutos_inactividad = getattr(settings, "INACTIVITY_TIMEOUT_MINUTES", 60)
        if ahora - sesion.ultimo_uso > timedelta(minutes=minutos_inactividad):
            self._sessions.revocar_familia(sesion.id_familia)
            raise AutenticacionError("Sesion cerrada por inactividad.")

        # Rotar y emitir nuevo par
        nuevo_refresh = secrets.token_urlsafe(48)
        nueva_sesion = self._sessions.rotar_sesion(sesion, nuevo_refresh, ip=ip)
        nuevo_access = self._generar_jwt_access(sesion.id_usuario, nueva_sesion.id_sesion)

        return nuevo_access, nuevo_refresh

    def cerrar_sesion(self, refresh_token: str) -> None:
        """Revoca la sesión activa."""
        sesion = self._sessions.buscar_por_token(refresh_token)
        if sesion and not sesion.revocada:
            self._sessions.revocar_familia(sesion.id_familia)

    def _generar_jwt_access(self, usuario: Any, id_sesion: int) -> str:
        """Genera token JWT de 15 min sin permisos embebidos (ADR-006)."""
        minutos_vida = getattr(settings, "ACCESS_TOKEN_LIFETIME_MINUTES", 15)
        ahora = int(time.time())
        exp = ahora + (minutos_vida * 60)

        payload = {
            "sub": str(usuario.id_usuario),
            "email": usuario.email,
            "rol": usuario.id_rol.nombre,
            "sid": id_sesion,
            "jti": str(uuid.uuid4()),
            "iat": ahora,
            "exp": exp,
        }

        signing_key = getattr(settings, "JWT_SIGNING_KEY", "secret")
        key_id = getattr(settings, "JWT_KEY_ID", "k1")
        return jwt.encode(payload, signing_key, algorithm="HS256", headers={"kid": key_id})


class PermissionService:
    """Servicio de verificación de permisos en servidor (ADR-007)."""

    def __init__(self, repo: PermissionRepository | None = None) -> None:
        self._repo = repo or PermissionRepository()

    def tiene_permiso(self, ctx: AuthContext, modulo: str, accion: str) -> bool:
        # Administrador tiene acceso irrestricto si es global
        if ctx.es_global and ctx.rol_nombre == "Administrador":
            return True

        if ctx.id_rol is not None:
            return self._repo.tiene_permiso(ctx.id_usuario, ctx.id_rol, modulo, accion)

        # Consultar repositorio para evaluar override -> rol -> deny
        from apps.m01_identidad.models import Usuarios
        try:
            usr_model = Usuarios.objects.only("id_rol_id").get(pk=ctx.id_usuario)
            return self._repo.tiene_permiso(ctx.id_usuario, usr_model.id_rol_id, modulo, accion)
        except Exception:
            return False

