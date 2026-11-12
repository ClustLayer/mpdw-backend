# ==============================================================================
# Repositorios de Identidad y Sesión - MPDW
# SAD Ref: M01, ADR-006, ADR-007, §10.3, §10.4
# ==============================================================================
import hashlib
import hmac
from datetime import timedelta
from uuid import UUID

from django.db import transaction
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

    def incrementar_intentos_fallidos(
        self, usuario: Usuarios, max_intentos: int = 5, minutos_bloqueo: int = 15
    ) -> bool:
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

    def bloquear_para_emision_2fa(self, id_usuario: int) -> Usuarios:
        """Bloqueo pessimista del usuario para serializar emision de codigos 2FA."""
        return Usuarios.objects.select_for_update().select_related("id_rol").get(pk=id_usuario)

    def incrementar_credential_version(self, usuario: Usuarios) -> int:
        with transaction.atomic():
            bloqueado = Usuarios.objects.select_for_update().get(pk=usuario.pk)
            bloqueado.credential_version = int(bloqueado.credential_version or 1) + 1
            bloqueado.save(update_fields=["credential_version"])
            usuario.credential_version = bloqueado.credential_version
            return bloqueado.credential_version

    def obtener_sedes_asignadas_ids(self, id_usuario: int) -> tuple[int, ...]:
        return tuple(
            Usuario_sede.objects.filter(id_usuario_id=id_usuario, estado=True).values_list(
                "id_sede_id", flat=True
            )
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

    def _mapas(self, id_usuario: int, id_rol: int) -> tuple[dict[tuple[str, str], bool], dict[tuple[str, str], bool]]:
        clave = (id_usuario, id_rol)
        cache = getattr(self, "_perm_cache", None)
        if cache and cache[0] == clave:
            return cache[1], cache[2]
        overrides: dict[tuple[str, str], bool] = {}
        for up in Usuario_permiso.objects.filter(id_usuario_id=id_usuario).select_related("id_permiso"):
            permiso = up.id_permiso
            if permiso.estado:
                overrides[(permiso.modulo, permiso.accion)] = bool(up.permitido)
        rol_map: dict[tuple[str, str], bool] = {}
        for rp in Rol_permiso.objects.filter(id_rol_id=id_rol, permitido=True).select_related("id_permiso"):
            permiso = rp.id_permiso
            if permiso.estado:
                rol_map[(permiso.modulo, permiso.accion)] = True
        self._perm_cache = (clave, overrides, rol_map)
        return overrides, rol_map

    def _efectivo_permitido(self, id_usuario: int, id_rol: int, modulo: str, accion: str) -> bool | None:
        overrides, rol_map = self._mapas(id_usuario, id_rol)
        if (modulo, accion) in overrides:
            return overrides[(modulo, accion)]
        if rol_map.get((modulo, accion)):
            return True
        return None

    def _bloqueado_sin_acceso(self, id_usuario: int, id_rol: int, modulo: str) -> bool:
        efectivo = self._efectivo_permitido(id_usuario, id_rol, modulo, "Sin acceso")
        return efectivo is True

    def tiene_permiso(self, id_usuario: int, id_rol: int, modulo: str, accion: str) -> bool:
        """
        Regla BR-10 + equivalencias Total/T y bloqueo Sin acceso.
        """
        from apps.m01_identidad.permiso_eval import candidatas_para

        if self._bloqueado_sin_acceso(id_usuario, id_rol, modulo):
            return False
        for candidata in candidatas_para(accion):
            efectivo = self._efectivo_permitido(id_usuario, id_rol, modulo, candidata)
            if efectivo is True:
                return True
            if efectivo is False:
                continue
        return False

    def acciones_por_modulo(self, id_usuario: int, id_rol: int) -> dict[str, set[str]]:
        """Acciones efectivas agrupadas por módulo de dominio (HU 18)."""
        from apps.m01_identidad.models import Permisos

        resultado: dict[str, set[str]] = {}
        permisos = Permisos.objects.filter(estado=True).only("id_permiso", "modulo", "accion")
        overrides = {
            up.id_permiso_id: up.permitido
            for up in Usuario_permiso.objects.filter(id_usuario_id=id_usuario).only(
                "id_permiso_id", "permitido"
            )
        }
        rol_map = {
            rp.id_permiso_id: rp.permitido
            for rp in Rol_permiso.objects.filter(id_rol_id=id_rol, permitido=True).only(
                "id_permiso_id", "permitido"
            )
        }
        for p in permisos:
            if p.id_permiso in overrides:
                if not overrides[p.id_permiso]:
                    continue
            elif p.id_permiso not in rol_map:
                continue
            resultado.setdefault(p.modulo, set()).add(p.accion)
        for modulo in list(resultado.keys()):
            if "Sin acceso" in resultado[modulo]:
                resultado[modulo] = {"Sin acceso"}
        return resultado


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
            return Tokens_recuperacion.objects.select_related(
                "id_usuario", "id_usuario__id_rol"
            ).get(token_hash=token_hash)
        except Tokens_recuperacion.DoesNotExist:
            return None

    def marcar_usado(self, registro: Tokens_recuperacion) -> None:
        registro.usado = True
        registro.save(update_fields=["usado"])

    def consumir_token_atomico(self, token: str) -> Tokens_recuperacion | None:
        """Marca el token como usado solo si sigue pendiente (una fila afectada)."""
        token_hash = SessionRepository.calcular_hash(token)
        with transaction.atomic():
            registro = (
                Tokens_recuperacion.objects.select_for_update()
                .select_related("id_usuario", "id_usuario__id_rol")
                .filter(token_hash=token_hash, usado=False)
                .first()
            )
            if registro is None:
                return None
            expira = getattr(registro, "expira_en", None)
            if not expira or timezone.now() > expira:
                return None
            actualizados = Tokens_recuperacion.objects.filter(pk=registro.pk, usado=False).update(
                usado=True
            )
            if actualizados != 1:
                return None
            registro.usado = True
            return registro


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
        with transaction.atomic():
            bloqueado = Codigos_2fa.objects.select_for_update().get(pk=registro.pk)
            bloqueado.intentos += 1
            if bloqueado.intentos >= max_intentos:
                bloqueado.usado = True
            bloqueado.save(update_fields=["intentos", "usado"])
            registro.intentos = bloqueado.intentos
            registro.usado = bloqueado.usado
            return bloqueado.intentos

    def marcar_usado(self, registro: Codigos_2fa) -> None:
        with transaction.atomic():
            Codigos_2fa.objects.filter(pk=registro.pk, usado=False).update(usado=True)
            registro.usado = True

    def crear_serializado(self, id_usuario: int, codigo: str, minutos: int) -> None:
        """Invalida vigentes y crea un unico codigo bajo bloqueo del usuario."""
        with transaction.atomic():
            Usuarios.objects.select_for_update().get(pk=id_usuario)
            Codigos_2fa.objects.filter(id_usuario_id=id_usuario, usado=False).update(usado=True)
            Codigos_2fa.objects.create(
                id_usuario_id=id_usuario,
                codigo_hash=SessionRepository.calcular_hash(codigo),
                expira_en=timezone.now() + timedelta(minutes=minutos),
                usado=False,
                intentos=0,
            )

    def intentar_consumir_codigo(
        self, id_usuario: int, codigo: str, max_intentos: int
    ) -> tuple[str, Codigos_2fa | None]:
        """
        Retorna ('ok', registro), ('invalido', registro) o ('expirado', None).
        Serializa verificacion y conteo de fallos sobre la fila del codigo vigente.
        """
        esperado = SessionRepository.calcular_hash(codigo.strip())
        with transaction.atomic():
            Usuarios.objects.select_for_update().get(pk=id_usuario)
            registro = (
                Codigos_2fa.objects.select_for_update()
                .filter(id_usuario_id=id_usuario, usado=False)
                .order_by("-id_codigo")
                .first()
            )
            if registro is None:
                return "expirado", None
            expira = getattr(registro, "expira_en", None)
            if not expira or timezone.now() > expira:
                registro.usado = True
                registro.save(update_fields=["usado"])
                return "expirado", None
            if not hmac.compare_digest(esperado, registro.codigo_hash):
                registro.intentos += 1
                if registro.intentos >= max_intentos:
                    registro.usado = True
                registro.save(update_fields=["intentos", "usado"])
                if registro.usado:
                    return "expirado", registro
                return "invalido", registro
            registro.usado = True
            registro.save(update_fields=["usado"])
            return "ok", registro
