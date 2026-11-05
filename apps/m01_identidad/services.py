# ==============================================================================
# Servicios de Autenticación y Autorización - MPDW
# HU_MPDW_01_01 a HU_MPDW_01_06. SAD Ref: M01, ADR-006, ADR-007
# ==============================================================================
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import jwt
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.m01_identidad.mensajes import (
    MSG_2FA_ERROR,
    MSG_2FA_EXPIRADO,
    MSG_2FA_INVALIDO,
    MSG_2FA_OK,
    MSG_2FA_REENVIADO,
    MSG_BIENVENIDA,
    MSG_BLOQUEADO,
    MSG_CAMBIO_OK,
    MSG_CAMPOS_OBLIGATORIOS,
    MSG_CREDENCIALES,
    MSG_ERROR_LOGIN,
    MSG_ERROR_SOLICITUD,
    MSG_INACTIVIDAD,
    MSG_LOGOUT_FALLO,
    MSG_LOGOUT_OK,
    MSG_PASSWORD_ACTUAL,
    MSG_PASSWORD_DISTINTA,
    MSG_RECUPERACION_OK,
    MSG_RESET_INVALIDO,
    MSG_RESET_OK,
    MSG_SESION_EXPIRADA,
)
from apps.m01_identidad.politicas import validar_politica_password
from apps.m01_identidad.repositories import (
    Codigo2FARepository,
    PermissionRepository,
    RecuperacionRepository,
    SessionRepository,
    UserRepository,
)
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import AutenticacionError, DominioError, ReglaNegocioError
from contratos.puertos.auditoria import AuditPort
from contratos.puertos.correo import EmailPort


@dataclass
class ResultadoLogin:
    access_token: str | None
    refresh_token: str | None
    ctx: AuthContext | None
    mensaje: str
    nombre: str
    debe_cambiar_password: bool
    requiere_2fa: bool
    desafio_token: str | None
    redireccion: str


def emitir_codigo_2fa(
    codigos: Codigo2FARepository,
    email_port: EmailPort | None,
    usuario: Any,
    mensaje_fallo: str,
    minutos_vigencia: int | None = None,
) -> None:
    """Genera un codigo de 6 digitos, guarda solo su hash y lo envia por correo."""
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    minutos = minutos_vigencia if minutos_vigencia is not None else int(settings.CODIGO_2FA_MINUTOS)
    minutos = max(1, minutos)
    codigos.crear_serializado(usuario.id_usuario, codigo, minutos)
    enviado = bool(email_port and email_port.enviar_codigo_2fa(usuario.email, codigo))
    if not enviado:
        raise AutenticacionError(mensaje_fallo, codigo="ERROR_CORREO")


def _requiere_2fa(usuario: Any) -> bool:
    rol = getattr(getattr(usuario, "id_rol", None), "nombre", "")
    return bool(getattr(usuario, "dosfa_habilitado", False)) and rol == "Administrador"


def _nombre(usuario: Any) -> str:
    return getattr(usuario, "nombre", None) or usuario.email


class AuthService:
    """Inicio de sesión, rotación opaca, cierre y emisión de tokens."""

    def __init__(
        self,
        user_repo: UserRepository | None = None,
        session_repo: SessionRepository | None = None,
        audit_port: AuditPort | None = None,
        email_port: EmailPort | None = None,
        codigo_repo: Codigo2FARepository | None = None,
    ) -> None:
        self._users = user_repo or UserRepository()
        self._sessions = session_repo or SessionRepository()
        self._audit = audit_port
        self._email = email_port
        self._codigos = codigo_repo or Codigo2FARepository()

    def autenticar(
        self,
        email: str,
        password: str,
        ip: str = "127.0.0.1",
        user_agent: str = "Unknown",
        id_correlacion: str = "",
    ) -> ResultadoLogin:
        usuario = self._users.buscar_por_email(email.strip())
        if usuario and usuario.esta_bloqueado:
            raise AutenticacionError(MSG_BLOQUEADO, codigo="CUENTA_BLOQUEADA")
        if not self._credenciales_validas(usuario, password):
            self._registrar_fallo(usuario, ip, user_agent, id_correlacion)
            raise AutenticacionError(MSG_CREDENCIALES, codigo="CREDENCIALES_INVALIDAS")

        assert usuario is not None
        self._users.registrar_acceso_exitoso(usuario)
        if getattr(usuario, "debe_cambiar_password", False) or not _requiere_2fa(usuario):
            return self._emitir_sesion(usuario, ip, user_agent, id_correlacion, mfa_verificada=not _requiere_2fa(usuario))
        return self._iniciar_desafio(usuario, ip)

    def rotar_refresh_token(
        self,
        refresh_token: str,
        ip: str = "127.0.0.1",
        id_correlacion: str = "",
    ) -> tuple[str, str]:
        sesion = self._sessions.buscar_por_token(refresh_token)
        if not sesion:
            raise AutenticacionError(MSG_SESION_EXPIRADA, codigo="SESION_EXPIRADA")
        if sesion.revocada or sesion.reemplazada_por:
            self._revocar_por_reuso(sesion, ip, id_correlacion)
            raise AutenticacionError(MSG_SESION_EXPIRADA, codigo="SESION_REVOCADA")

        ahora = timezone.now()
        if ahora > sesion.fecha_expiracion_absoluta:
            self._sessions.revocar_familia(sesion.id_familia)
            raise AutenticacionError(MSG_SESION_EXPIRADA, codigo="SESION_EXPIRADA")

        minutos = int(settings.INACTIVITY_TIMEOUT_MINUTES)
        if ahora - sesion.ultimo_uso > timedelta(minutes=minutos):
            self._sessions.revocar_familia(sesion.id_familia)
            raise AutenticacionError(MSG_INACTIVIDAD, codigo="SESION_INACTIVA")

        nuevo_refresh = secrets.token_urlsafe(48)
        nueva = self._sessions.rotar_sesion(sesion, nuevo_refresh, ip=ip)
        mfa_pendiente = not bool(getattr(sesion, "mfa_verificada", True))
        nuevo_access = self.emitir_access(sesion.id_usuario, nueva.id_sesion, mfa_pendiente=mfa_pendiente)
        return nuevo_access, nuevo_refresh

    def cerrar_sesion(self, refresh_token: str) -> str:
        try:
            sesion = self._sessions.buscar_por_token(refresh_token)
        except Exception as exc:
            raise DominioError(MSG_LOGOUT_FALLO, codigo="LOGOUT_FALLO") from exc
        if sesion is None or sesion.revocada or self._sesion_no_vigente(sesion):
            raise AutenticacionError(MSG_SESION_EXPIRADA, codigo="SESION_EXPIRADA")
        self._sessions.revocar_familia(sesion.id_familia)
        return MSG_LOGOUT_OK

    def emitir_access(self, usuario: Any, id_sesion: int, mfa_pendiente: bool = False) -> str:
        minutos_vida = int(settings.ACCESS_TOKEN_LIFETIME_MINUTES)
        ahora = int(time.time())
        payload: dict[str, Any] = {
            "sub": str(usuario.id_usuario),
            "email": usuario.email,
            "rol": usuario.id_rol.nombre,
            "sid": id_sesion,
            "typ": "access",
            "jti": str(uuid.uuid4()),
            "iat": ahora,
            "exp": ahora + (minutos_vida * 60),
        }
        if getattr(usuario, "debe_cambiar_password", False):
            payload["mcp"] = True
        if mfa_pendiente:
            payload["mfa_pendiente"] = True
        payload["cv"] = int(getattr(usuario, "credential_version", 1) or 1)
        return self._firmar(payload)

    def emitir_desafio(self, usuario: Any, exp_epoch: int | None = None) -> str:
        ahora = int(time.time())
        minutos = int(settings.CODIGO_2FA_MINUTOS)
        exp = exp_epoch if exp_epoch is not None else ahora + (minutos * 60)
        payload = {
            "sub": str(usuario.id_usuario),
            "typ": "2fa",
            "jti": str(uuid.uuid4()),
            "iat": ahora,
            "exp": exp,
        }
        return self._firmar(payload)

    def segundos_restantes_desafio(self, desafio_token: str) -> int:
        try:
            payload = jwt.decode(
                desafio_token,
                settings.JWT_SIGNING_KEY,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
        except jwt.PyJWTError:
            return 0
        if payload.get("typ") != "2fa":
            return 0
        return max(0, int(payload.get("exp", 0)) - int(time.time()))

    def usuario_desde_desafio(self, desafio_token: str) -> Any:
        try:
            payload = jwt.decode(desafio_token, settings.JWT_SIGNING_KEY, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise ReglaNegocioError(MSG_2FA_EXPIRADO, codigo="CODIGO_2FA_EXPIRADO") from exc
        if payload.get("typ") != "2fa":
            raise ReglaNegocioError(MSG_2FA_EXPIRADO, codigo="CODIGO_2FA_EXPIRADO")
        usuario = self._users.buscar_por_id(int(payload["sub"]))
        if not usuario or not usuario.estado:
            raise ReglaNegocioError(MSG_2FA_EXPIRADO, codigo="CODIGO_2FA_EXPIRADO")
        return usuario

    def _credenciales_validas(self, usuario: Any, password: str) -> bool:
        return bool(usuario and usuario.estado and usuario.check_password(password))

    def _registrar_fallo(self, usuario: Any, ip: str, user_agent: str, id_correlacion: str) -> None:
        if not usuario or not usuario.estado:
            return
        bloqueado = self._users.incrementar_intentos_fallidos(
            usuario,
            max_intentos=int(settings.MAX_INTENTOS_FALLIDOS),
            minutos_bloqueo=int(settings.BLOQUEO_MINUTOS),
        )
        if bloqueado is True or getattr(usuario, "esta_bloqueado", False):
            self._auditar(
                usuario,
                "BLOQUEO_POR_INTENTOS",
                "Usuarios",
                usuario.id_usuario,
                None,
                {"estado": "bloqueado"},
                "Tope de intentos fallidos",
                ip,
                user_agent,
                id_correlacion,
                resultado="RECHAZADO",
            )
            raise AutenticacionError(MSG_BLOQUEADO, codigo="CUENTA_BLOQUEADA")

    def _emitir_sesion(
        self,
        usuario: Any,
        ip: str,
        user_agent: str,
        id_correlacion: str,
        mfa_verificada: bool,
    ) -> ResultadoLogin:
        id_familia = uuid.uuid4()
        refresh_token = secrets.token_urlsafe(48)
        sesion = self._sessions.registrar_sesion(
            usuario=usuario,
            refresh_token=refresh_token,
            id_familia=id_familia,
            duracion_dias=int(settings.REFRESH_TOKEN_LIFETIME_DAYS),
            ip=ip,
            mfa_verificada=mfa_verificada,
        )
        sedes = self._users.obtener_sedes_asignadas_ids(usuario.id_usuario)
        ctx = self._contexto(usuario, sedes, ip, user_agent, id_correlacion)
        access = self.emitir_access(usuario, sesion.id_sesion, mfa_pendiente=not mfa_verificada)
        self._auditar(
            usuario,
            "LOGIN_EXITOSO",
            "Usuarios",
            usuario.id_usuario,
            None,
            {"email": usuario.email, "id_familia": str(id_familia)},
            "Inicio de sesion exitoso",
            ip,
            user_agent,
            id_correlacion,
        )
        debe = bool(getattr(usuario, "debe_cambiar_password", False))
        requiere = not mfa_verificada
        if debe:
            redireccion = "cambiar-contrasena"
        elif requiere:
            redireccion = "verificacion-2fa"
        else:
            redireccion = self._inicio_de_rol(usuario)
        return ResultadoLogin(
            access_token=access,
            refresh_token=refresh_token,
            ctx=ctx,
            mensaje=MSG_BIENVENIDA.format(nombre=_nombre(usuario)),
            nombre=_nombre(usuario),
            debe_cambiar_password=debe,
            requiere_2fa=requiere,
            desafio_token=None,
            redireccion=redireccion,
        )

    def _iniciar_desafio(self, usuario: Any, ip: str) -> ResultadoLogin:
        emitir_codigo_2fa(self._codigos, self._email, usuario, MSG_ERROR_LOGIN)
        sedes = self._users.obtener_sedes_asignadas_ids(usuario.id_usuario)
        return ResultadoLogin(
            access_token=None,
            refresh_token=None,
            ctx=self._contexto(usuario, sedes, ip, "Unknown", ""),
            mensaje="",
            nombre=_nombre(usuario),
            debe_cambiar_password=False,
            requiere_2fa=True,
            desafio_token=self.emitir_desafio(usuario),
            redireccion="verificacion-2fa",
        )

    def _revocar_por_reuso(self, sesion: Any, ip: str, id_correlacion: str) -> None:
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
                    motivo="Reuso de refresh token. Familia revocada.",
                    resultado="RECHAZADO",
                    id_correlacion=id_correlacion,
                    ip=ip,
                )
            )

    def _sesion_no_vigente(self, sesion: Any) -> bool:
        ahora = timezone.now()
        expira = getattr(sesion, "fecha_expiracion_absoluta", None)
        if expira is not None and ahora > expira:
            return True
        ultimo = getattr(sesion, "ultimo_uso", None)
        if ultimo is None:
            return False
        return ahora - ultimo > timedelta(minutes=int(settings.INACTIVITY_TIMEOUT_MINUTES))

    def _contexto(self, usuario: Any, sedes: tuple[int, ...], ip: str, user_agent: str, correlacion: str) -> AuthContext:
        return AuthContext(
            id_usuario=usuario.id_usuario,
            email=usuario.email,
            rol_nombre=usuario.id_rol.nombre,
            sedes_asignadas=sedes,
            es_global=usuario.id_rol.nombre == "Administrador",
            ip=ip,
            user_agent=user_agent,
            id_correlacion=correlacion,
        )

    def _inicio_de_rol(self, usuario: Any) -> str:
        rol = usuario.id_rol.nombre
        if rol == "Administrador":
            return "panel-administrador"
        if rol == "Gerente":
            return "panel-gerente"
        return "panel-empleado"

    def _auditar(
        self,
        usuario: Any,
        accion: str,
        entidad: str,
        id_entidad: int,
        antes: dict[str, Any] | None,
        despues: dict[str, Any] | None,
        motivo: str,
        ip: str,
        user_agent: str,
        correlacion: str,
        resultado: str = "EXITO",
    ) -> None:
        if not self._audit:
            return
        self._audit.registrar(
            AuditoriaDTO(
                id_usuario=usuario.id_usuario,
                accion=accion,
                entidad=entidad,
                id_entidad=id_entidad,
                datos_antes=antes,
                datos_despues=despues,
                motivo=motivo,
                resultado=resultado,
                id_correlacion=correlacion,
                ip=ip,
                user_agent=user_agent,
            )
        )

    def _firmar(self, payload: dict[str, Any]) -> str:
        return jwt.encode(
            payload,
            settings.JWT_SIGNING_KEY,
            algorithm="HS256",
            headers={"kid": settings.JWT_KEY_ID},
        )


class RecuperacionService:
    """Solicitud y restablecimiento de contraseña con token de un solo uso."""

    def __init__(
        self,
        user_repo: UserRepository | None = None,
        session_repo: SessionRepository | None = None,
        token_repo: RecuperacionRepository | None = None,
        email_port: EmailPort | None = None,
    ) -> None:
        self._users = user_repo or UserRepository()
        self._sessions = session_repo or SessionRepository()
        self._tokens = token_repo or RecuperacionRepository()
        self._email = email_port

    def solicitar(self, email: str) -> str:
        try:
            usuario = self._users.buscar_por_email(email.strip())
            if usuario and usuario.estado and not usuario.esta_bloqueado:
                token = secrets.token_urlsafe(32)
                self._tokens.invalidar_pendientes(usuario.id_usuario)
                self._tokens.crear(usuario, token, int(settings.RECUPERACION_MINUTOS))
                enlace = f"{settings.FRONTEND_URL}/nueva-contrasena#rt={token}"
                if self._email:
                    self._email.enviar_recuperacion_password(usuario.email, enlace)
            return MSG_RECUPERACION_OK
        except Exception as exc:
            raise DominioError(MSG_ERROR_SOLICITUD, codigo="ERROR_RECUPERACION") from exc

    def restablecer(self, token: str, nueva: str, confirmar: str) -> str:
        if not nueva or not confirmar:
            raise ReglaNegocioError(MSG_CAMPOS_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        if nueva != confirmar:
            raise ReglaNegocioError(MSG_PASSWORD_DISTINTA, codigo="PASSWORD_NO_COINCIDE")
        validar_politica_password(nueva)
        registro = self._tokens.consumir_token_atomico(token)
        if registro is None:
            raise ReglaNegocioError(MSG_RESET_INVALIDO, codigo="TOKEN_RECUPERACION_INVALIDO")
        usuario = registro.id_usuario
        with transaction.atomic():
            usuario.set_password(nueva)
            usuario.debe_cambiar_password = False
            usuario.credential_version = int(getattr(usuario, "credential_version", 1) or 1) + 1
            usuario.save(update_fields=["password", "debe_cambiar_password", "credential_version"])
            self._sessions.revocar_usuario(usuario.id_usuario)
        return MSG_RESET_OK

    def _vigente(self, registro: Any) -> bool:
        if registro is None or registro.usado:
            return False
        expira = getattr(registro, "expira_en", None) or getattr(registro, "fecha_expiracion", None)
        return bool(expira and timezone.now() <= expira)

    def _guardar_usuario(self, usuario: Any) -> None:
        if hasattr(usuario, "save"):
            usuario.save(update_fields=["password", "debe_cambiar_password"])


class ContrasenaService:
    """Cambio de contraseña autenticado (HU 04)."""

    def __init__(
        self,
        auth: AuthService | None = None,
        audit_port: AuditPort | None = None,
    ) -> None:
        self._auth = auth or AuthService()
        self._audit = audit_port

    def cambiar(
        self,
        usuario: Any,
        actual: str,
        nueva: str,
        confirmar: str,
        id_sesion: int,
        mfa_pendiente: bool,
        ip: str,
        user_agent: str,
        id_correlacion: str,
    ) -> tuple[str, str, bool, str | None]:
        if not actual or not nueva or not confirmar:
            raise ReglaNegocioError(MSG_CAMPOS_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        if not usuario.check_password(actual):
            raise ReglaNegocioError(MSG_PASSWORD_ACTUAL, codigo="PASSWORD_ACTUAL_INCORRECTA")
        if nueva != confirmar:
            raise ReglaNegocioError(MSG_PASSWORD_DISTINTA, codigo="PASSWORD_NO_COINCIDE")
        validar_politica_password(nueva, password_actual=actual)
        antes = {"debe_cambiar_password": bool(getattr(usuario, "debe_cambiar_password", False))}
        codigo_repo = self._auth._codigos
        email_port = self._auth._email
        desafio_token: str | None = None
        with transaction.atomic():
            usuario.set_password(nueva)
            usuario.debe_cambiar_password = False
            usuario.credential_version = int(getattr(usuario, "credential_version", 1) or 1) + 1
            if hasattr(usuario, "save"):
                usuario.save(update_fields=["password", "debe_cambiar_password", "credential_version"])
            if self._audit:
                self._audit.registrar(
                    AuditoriaDTO(
                        id_usuario=usuario.id_usuario,
                        accion="CAMBIO_PASSWORD",
                        entidad="Usuarios",
                        id_entidad=usuario.id_usuario,
                        datos_antes=antes,
                        datos_despues={"debe_cambiar_password": False, "password": "[omitido]"},
                        motivo="Cambio de contraseña",
                        id_correlacion=id_correlacion,
                        ip=ip,
                        user_agent=user_agent,
                    )
                )
        sigue_2fa = bool(mfa_pendiente and _requiere_2fa(usuario))
        if sigue_2fa:
            emitir_codigo_2fa(codigo_repo, email_port, usuario, MSG_2FA_ERROR)
            desafio_token = self._auth.emitir_desafio(usuario)
        access = self._auth.emitir_access(usuario, id_sesion, mfa_pendiente=sigue_2fa)
        return access, MSG_CAMBIO_OK, sigue_2fa, desafio_token


class Verificacion2FAService:
    """Verificación y reenvío del segundo factor del administrador."""

    def __init__(
        self,
        auth: AuthService | None = None,
        codigo_repo: Codigo2FARepository | None = None,
        email_port: EmailPort | None = None,
        session_repo: SessionRepository | None = None,
    ) -> None:
        self._auth = auth or AuthService(email_port=email_port, codigo_repo=codigo_repo)
        self._codigos = codigo_repo or Codigo2FARepository()
        self._email = email_port
        self._sessions = session_repo or SessionRepository()

    def verificar(
        self,
        usuario: Any | None,
        desafio_token: str,
        codigo: str,
        id_sesion: int | None,
        ip: str,
        user_agent: str,
        id_correlacion: str,
    ) -> ResultadoLogin:
        try:
            return self._verificar(usuario, desafio_token, codigo, id_sesion, ip, user_agent, id_correlacion)
        except (ReglaNegocioError, AutenticacionError):
            raise
        except Exception as exc:
            raise DominioError(MSG_2FA_ERROR, codigo="ERROR_2FA") from exc

    def reenviar(self, usuario: Any | None, desafio_token: str) -> tuple[str, str]:
        try:
            if usuario is None:
                usuario = self._auth.usuario_desde_desafio(desafio_token)
            restantes = self._auth.segundos_restantes_desafio(desafio_token)
            if restantes <= 0:
                raise ReglaNegocioError(MSG_2FA_EXPIRADO, codigo="CODIGO_2FA_EXPIRADO")
            minutos_codigo = max(1, (restantes + 59) // 60)
            emitir_codigo_2fa(self._codigos, self._email, usuario, MSG_2FA_ERROR, minutos_vigencia=minutos_codigo)
            try:
                payload = jwt.decode(
                    desafio_token,
                    settings.JWT_SIGNING_KEY,
                    algorithms=["HS256"],
                    options={"verify_exp": False},
                )
                exp = int(payload.get("exp", int(time.time()) + restantes))
            except jwt.PyJWTError:
                exp = int(time.time()) + restantes
            nuevo_desafio = self._auth.emitir_desafio(usuario, exp_epoch=exp)
            return MSG_2FA_REENVIADO, nuevo_desafio
        except (ReglaNegocioError, AutenticacionError):
            raise
        except Exception as exc:
            raise DominioError(MSG_2FA_ERROR, codigo="ERROR_2FA") from exc

    def _verificar(
        self,
        usuario: Any | None,
        desafio_token: str,
        codigo: str,
        id_sesion: int | None,
        ip: str,
        user_agent: str,
        id_correlacion: str,
    ) -> ResultadoLogin:
        if usuario is None:
            usuario = self._auth.usuario_desde_desafio(desafio_token)
        self._consumir_codigo(usuario, codigo)
        if id_sesion:
            self._sessions.marcar_mfa(id_sesion)
            access = self._auth.emitir_access(usuario, id_sesion, mfa_pendiente=False)
            return ResultadoLogin(
                access_token=access,
                refresh_token=None,
                ctx=None,
                mensaje=MSG_2FA_OK,
                nombre=_nombre(usuario),
                debe_cambiar_password=bool(getattr(usuario, "debe_cambiar_password", False)),
                requiere_2fa=False,
                desafio_token=None,
                redireccion="cambiar-contrasena" if getattr(usuario, "debe_cambiar_password", False) else self._auth._inicio_de_rol(usuario),
            )
        resultado = self._auth._emitir_sesion(usuario, ip, user_agent, id_correlacion, mfa_verificada=True)
        return ResultadoLogin(
            access_token=resultado.access_token,
            refresh_token=resultado.refresh_token,
            ctx=resultado.ctx,
            mensaje=MSG_2FA_OK,
            nombre=resultado.nombre,
            debe_cambiar_password=resultado.debe_cambiar_password,
            requiere_2fa=False,
            desafio_token=None,
            redireccion=resultado.redireccion,
        )

    def _consumir_codigo(self, usuario: Any, codigo: str) -> None:
        estado, _ = self._codigos.intentar_consumir_codigo(
            usuario.id_usuario,
            codigo,
            int(settings.MAX_INTENTOS_2FA),
        )
        if estado == "ok":
            return
        if estado == "invalido":
            raise ReglaNegocioError(MSG_2FA_INVALIDO, codigo="CODIGO_2FA_INVALIDO")
        raise ReglaNegocioError(MSG_2FA_EXPIRADO, codigo="CODIGO_2FA_EXPIRADO")


class PermissionService:
    """Servicio de verificación de permisos en servidor (ADR-007)."""

    def __init__(self, repo: PermissionRepository | None = None) -> None:
        self._repo = repo or PermissionRepository()

    def tiene_permiso(self, ctx: AuthContext, modulo: str, accion: str) -> bool:
        if ctx.es_global and ctx.rol_nombre == "Administrador":
            return True

        if ctx.id_rol is not None:
            return self._repo.tiene_permiso(ctx.id_usuario, ctx.id_rol, modulo, accion)

        from apps.m01_identidad.models import Usuarios

        try:
            usr_model = Usuarios.objects.only("id_rol_id").get(pk=ctx.id_usuario)
            return self._repo.tiene_permiso(ctx.id_usuario, usr_model.id_rol_id, modulo, accion)
        except Exception:
            return False
