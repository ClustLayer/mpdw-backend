# ==============================================================================
# Repositorios de Identidad y Sesión - MPDW
# SAD Ref: M01, ADR-006, ADR-007, §10.3, §10.4
# ==============================================================================
import hashlib
from datetime import timedelta
from uuid import UUID

from django.utils import timezone

from apps.m01_identidad.models import (
    Codigos_2fa,
    Rol_permiso,
    Sesiones_usuario,
    Tokens_recuperacion,
    Usuario_permiso,
    Usuario_sede,
    Usuarios,
)


class UserRepository:
    """Acceso a datos de Usuarios y sus sedes asignadas."""

    def buscar_por_email(self, email: str) -> Usuarios | None:
        try:
            return Usuarios.objects.select_related("id_rol").get(email__iexact=email)
        except Usuarios.DoesNotExist:
            return None

    def buscar_por_id(self, id_usuario: int) -> Usuarios | None:
        try:
            return Usuarios.objects.select_related("id_rol").get(pk=id_usuario)
        except Usuarios.DoesNotExist:
            return None

    def incrementar_intentos_fallidos(self, usuario: Usuarios, max_intentos: int = 5, minutos_bloqueo: int = 15) -> bool:
        usuario.intentos_fallidos += 1
        bloqueado = usuario.intentos_fallidos >= max_intentos
        if bloqueado:
            usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=minutos_bloqueo)
        usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        return bloqueado

    def restablecer_intentos_fallidos(self, usuario: Usuarios) -> None:
        if usuario.intentos_fallidos > 0 or usuario.bloqueado_hasta is not None:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])

    def registrar_acceso_exitoso(self, usuario: Usuarios) -> None:
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.ultimo_acceso = timezone.now()
        usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta", "ultimo_acceso"])

    def obtener_sedes_asignadas_ids(self, id_usuario: int) -> tuple[int, ...]:
        return tuple(
            Usuario_sede.objects.filter(id_usuario_id=id_usuario, estado=True).values_list("id_sede_id", flat=True)
        )


class SessionRepository:
    """Gestión de sesiones de usuario y rotación de refresh tokens."""

    @staticmethod
    def calcular_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def registrar_sesion(
        self,
        usuario: Usuarios,
        refresh_token: str,
        id_familia: UUID,
        duracion_dias: int,
        ip: str,
        mfa_verificada: bool = True,
    ) -> Sesiones_usuario:
        token_hash = self.calcular_hash(refresh_token)
        expiracion = timezone.now() + timedelta(days=duracion_dias)
        return Sesiones_usuario.objects.create(
            id_usuario=usuario,
            refresh_token_hash=token_hash,
            id_familia=id_familia,
            ip_origen=ip,
            fecha_expiracion_absoluta=expiracion,
            mfa_verificada=mfa_verificada,
        )

    def buscar_por_token(self, refresh_token: str) -> Sesiones_usuario | None:
        token_hash = self.calcular_hash(refresh_token)
        try:
            return Sesiones_usuario.objects.select_related("id_usuario", "id_usuario__id_rol").get(
                refresh_token_hash=token_hash
            )
        except Sesiones_usuario.DoesNotExist:
            return None

    def revocar_familia(self, id_familia: UUID) -> int:
        """Revoca todas las sesiones pertenecientes a una familia por detección de reuso."""
        ahora = timezone.now()
        return Sesiones_usuario.objects.filter(id_familia=id_familia, revocada=False).update(
            revocada=True,
            fecha_revocacion=ahora,
        )

    def marcar_mfa(self, id_sesion: int) -> None:
        Sesiones_usuario.objects.filter(pk=id_sesion).update(mfa_verificada=True)

    def revocar_usuario(self, id_usuario: int) -> int:
        ahora = timezone.now()
        return Sesiones_usuario.objects.filter(id_usuario_id=id_usuario, revocada=False).update(
            revocada=True,
            fecha_revocacion=ahora,
        )

    def rotar_sesion(
        self,
        sesion_actual: Sesiones_usuario,
        nuevo_token: str,
        ip: str,
    ) -> Sesiones_usuario:
        """Invalida la sesión actual enlazándola a la nueva para detectar reuso."""
        nuevo_hash = self.calcular_hash(nuevo_token)
        sesion_actual.reemplazada_por = nuevo_hash
        sesion_actual.revocada = True
        sesion_actual.fecha_revocacion = timezone.now()
        sesion_actual.save(update_fields=["reemplazada_por", "revocada", "fecha_revocacion"])

        return Sesiones_usuario.objects.create(
            id_usuario=sesion_actual.id_usuario,
            refresh_token_hash=nuevo_hash,
            id_familia=sesion_actual.id_familia,
            ip_origen=ip,
            fecha_expiracion_absoluta=sesion_actual.fecha_expiracion_absoluta,
            mfa_verificada=sesion_actual.mfa_verificada,
        )


class PermissionRepository:
    """Evaluación de permisos en servidor (BR-10, ADR-007)."""

    def tiene_permiso(self, id_usuario: int, id_rol: int, modulo: str, accion: str) -> bool:
        """
        Regla BR-10:
        1. Si existe excepción individual en Usuario_permiso: rige su valor 'permitido'.
        2. Si no, si existe asignación en Rol_permiso: True.
        3. En cualquier otro caso: False (Deny by default).
        """
        # 1. Verificar override individual
        excepcion = Usuario_permiso.objects.filter(
            id_usuario_id=id_usuario,
            id_permiso__modulo=modulo,
            id_permiso__accion=accion,
        ).first()

        if excepcion is not None:
            return bool(excepcion.permitido)

        # 2. Verificar permiso por rol base
        return Rol_permiso.objects.filter(
            id_rol_id=id_rol,
            id_permiso__modulo=modulo,
            id_permiso__accion=accion,
        ).exists()


class RecuperacionRepository:
    """Tokens de un solo uso. Solo se persiste el hash."""

    def invalidar_pendientes(self, id_usuario: int) -> None:
        Tokens_recuperacion.objects.filter(id_usuario_id=id_usuario, usado=False).update(usado=True)

    def crear(self, usuario: Usuarios, token: str, minutos: int) -> Tokens_recuperacion:
        return Tokens_recuperacion.objects.create(
            id_usuario=usuario,
            token_hash=SessionRepository.calcular_hash(token),
            expira_en=timezone.now() + timedelta(minutes=minutos),
            usado=False,
        )

    def buscar_por_token(self, token: str) -> Tokens_recuperacion | None:
        token_hash = SessionRepository.calcular_hash(token)
        try:
            return Tokens_recuperacion.objects.select_related("id_usuario", "id_usuario__id_rol").get(
                token_hash=token_hash
            )
        except Tokens_recuperacion.DoesNotExist:
            return None

    def marcar_usado(self, registro: Tokens_recuperacion) -> None:
        registro.usado = True
        registro.save(update_fields=["usado"])


class Codigo2FARepository:
    """Codigos de segundo factor. Solo se persiste el hash."""

    def invalidar_vigentes(self, id_usuario: int) -> None:
        Codigos_2fa.objects.filter(id_usuario_id=id_usuario, usado=False).update(usado=True)

    def crear(self, usuario: Usuarios, codigo: str, minutos: int) -> Codigos_2fa:
        return Codigos_2fa.objects.create(
            id_usuario=usuario,
            codigo_hash=SessionRepository.calcular_hash(codigo),
            expira_en=timezone.now() + timedelta(minutes=minutos),
            usado=False,
            intentos=0,
        )

    def buscar_vigente(self, id_usuario: int) -> Codigos_2fa | None:
        return (
            Codigos_2fa.objects.filter(id_usuario_id=id_usuario, usado=False)
            .order_by("-id_codigo")
            .first()
        )

    def registrar_fallo(self, registro: Codigos_2fa, max_intentos: int) -> int:
        registro.intentos += 1
        if registro.intentos >= max_intentos:
            registro.usado = True
        registro.save(update_fields=["intentos", "usado"])
        return registro.intentos

    def marcar_usado(self, registro: Codigos_2fa) -> None:
        registro.usado = True
        registro.save(update_fields=["usado"])

