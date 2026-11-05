# ==============================================================================
# Administracion de usuarios y perfil propio - Epic 2 (HU 07-12)
# ==============================================================================
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.m01_identidad.mensajes import (
    MSG_CAMPOS_OBLIGATORIOS,
    MSG_CONCURRENCIA,
    MSG_CONTRASENA_TEMP_ERROR,
    MSG_CONTRASENA_TEMP_OK,
    MSG_CONTRASENA_TEMP_PROPIA,
    MSG_DOCUMENTO_DUPLICADO,
    MSG_EMAIL_DUPLICADO,
    MSG_EMAIL_INVALIDO,
    MSG_ESTADO_ACTUALIZADO,
    MSG_ESTADO_ERROR,
    MSG_LISTADO_USUARIOS,
    MSG_LISTADO_VACIO,
    MSG_PERFIL_ACTUALIZADO,
    MSG_PERFIL_ERROR,
    MSG_ROL_INACTIVO,
    MSG_ROL_PROPIO,
    MSG_SEDE_OBLIGATORIA,
    MSG_USUARIO_ACTUALIZADO,
    MSG_USUARIO_ACTUALIZAR_ERROR,
    MSG_USUARIO_CREADO,
    MSG_USUARIO_CREAR_ERROR,
)
from apps.m01_identidad.models import Roles, Usuario_sede, Usuarios
from apps.m01_identidad.politicas import (
    correo_valido,
    exigir_documento,
    exigir_telefono,
    generar_contrasena_inicial,
)
from apps.m01_identidad.repositories import SessionRepository, UserRepository
from apps.m01_identidad.usuario_util import estado_etiqueta, nombre_completo, snapshot_usuario
from apps.m02_sedes.models import Sedes
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import DominioError, ReglaNegocioError
from contratos.puertos.auditoria import AuditPort
from contratos.puertos.correo import EmailPort

logger = logging.getLogger(__name__)

ORDEN_PERMITIDO = {
    "nombre_completo": ("nombre", "apellido"),
    "nombre": ("nombre",),
    "apellido": ("apellido",),
    "documento": ("documento",),
    "email": ("email",),
    "rol": ("id_rol__nombre",),
    "estado": ("estado",),
    "ultimo_acceso": ("ultimo_acceso",),
}


@dataclass(frozen=True)
class PaginaUsuarios:
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    mensaje: str


def _sedes_payload(sedes: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not sedes:
        return []
    return [{"id_sede": int(s["id_sede"]), "es_principal": bool(s.get("es_principal"))} for s in sedes]


class AdminUsuariosService:
    def __init__(
        self,
        audit_port: AuditPort | None = None,
        email_port: EmailPort | None = None,
        users: UserRepository | None = None,
        sessions: SessionRepository | None = None,
    ) -> None:
        self._audit = audit_port
        self._email = email_port
        self._users = users or UserRepository()
        self._sessions = sessions or SessionRepository()

    def listar(
        self,
        q: str,
        id_rol: int | None,
        estado_filtro: str,
        page: int,
        page_size: int,
        ordering: str,
    ) -> PaginaUsuarios:
        qs = Usuarios.objects.select_related("id_rol").all()
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(nombre__icontains=texto)
                | Q(apellido__icontains=texto)
                | Q(documento__icontains=texto)
                | Q(email__icontains=texto)
            )
        if id_rol:
            qs = qs.filter(id_rol_id=id_rol)
        ahora = timezone.now()
        filtro = (estado_filtro or "todos").lower()
        if filtro == "activo":
            qs = qs.filter(estado=True).filter(Q(bloqueado_hasta__isnull=True) | Q(bloqueado_hasta__lte=ahora))
        elif filtro == "inactivo":
            qs = qs.filter(estado=False)
        elif filtro == "bloqueado":
            qs = qs.filter(bloqueado_hasta__gt=ahora)

        orden = (ordering or "-ultimo_acceso").strip()
        desc = orden.startswith("-")
        clave = orden[1:] if desc else orden
        campos = ORDEN_PERMITIDO.get(clave, ("ultimo_acceso",))
        orden_sql = [("-" if desc else "") + c for c in campos]
        qs = qs.order_by(*orden_sql, "id_usuario")

        total = qs.count()
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        inicio = (page - 1) * page_size
        filas = list(qs[inicio : inicio + page_size])
        items = [self._fila_listado(u) for u in filas]
        if total == 0:
            mensaje = MSG_LISTADO_VACIO
        else:
            mensaje = MSG_LISTADO_USUARIOS.format(n=len(items), total=total)
        return PaginaUsuarios(items=items, total=total, page=page, page_size=page_size, mensaje=mensaje)

    def obtener_detalle(self, id_usuario: int) -> dict[str, Any]:
        usuario = self._users.buscar_por_id(id_usuario)
        if not usuario:
            raise ReglaNegocioError("Usuario no encontrado.", codigo="USUARIO_NO_ENCONTRADO")
        return self._detalle(usuario)

    def crear(self, ctx: AuthContext, datos: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        try:
            return self._crear(ctx, datos)
        except ReglaNegocioError:
            raise
        except Exception as exc:
            logger.exception("Fallo al crear usuario")
            raise DominioError(MSG_USUARIO_CREAR_ERROR, codigo="ERROR_CREAR_USUARIO") from exc

    def actualizar(self, ctx: AuthContext, id_usuario: int, datos: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        try:
            return self._actualizar(ctx, id_usuario, datos)
        except ReglaNegocioError:
            raise
        except Exception as exc:
            logger.exception("Fallo al actualizar usuario %s", id_usuario)
            raise DominioError(MSG_USUARIO_ACTUALIZAR_ERROR, codigo="ERROR_ACTUALIZAR_USUARIO") from exc

    def cambiar_estado(self, ctx: AuthContext, id_usuario: int, accion: str) -> str:
        try:
            return self._cambiar_estado(ctx, id_usuario, accion)
        except ReglaNegocioError:
            raise
        except Exception as exc:
            logger.exception("Fallo al cambiar estado de usuario %s", id_usuario)
            raise DominioError(MSG_ESTADO_ERROR, codigo="ERROR_CAMBIAR_ESTADO") from exc

    def generar_contrasena_temporal(self, ctx: AuthContext, id_usuario: int) -> tuple[str, str]:
        if ctx.id_usuario == id_usuario:
            raise ReglaNegocioError(MSG_CONTRASENA_TEMP_PROPIA, codigo="CONTRASENA_TEMP_PROPIA")
        try:
            return self._generar_contrasena_temporal(ctx, id_usuario)
        except ReglaNegocioError:
            raise
        except Exception as exc:
            logger.exception("Fallo al generar contrasena temporal")
            raise DominioError(MSG_CONTRASENA_TEMP_ERROR, codigo="ERROR_CONTRASENA_TEMP") from exc

    def _crear(self, ctx: AuthContext, datos: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        self._validar_obligatorios_creacion(datos)
        email = str(datos["email"]).strip()
        documento = str(datos["documento"]).strip()
        if not correo_valido(email):
            raise ReglaNegocioError(MSG_EMAIL_INVALIDO, codigo="EMAIL_INVALIDO")
        exigir_documento(documento)
        exigir_telefono(str(datos.get("telefono") or ""))
        if Usuarios.objects.filter(email__iexact=email).exists():
            raise ReglaNegocioError(MSG_EMAIL_DUPLICADO, codigo="EMAIL_DUPLICADO")
        if Usuarios.objects.filter(documento=documento).exists():
            raise ReglaNegocioError(MSG_DOCUMENTO_DUPLICADO, codigo="DOCUMENTO_DUPLICADO")
        rol = self._rol_activo(int(datos["id_rol"]))
        sedes = _sedes_payload(datos.get("sedes"))
        self._validar_sedes(sedes)
        clave = generar_contrasena_inicial()
        expira = timezone.now() + timedelta(hours=24)
        with transaction.atomic():
            usuario = Usuarios.objects.create(
                email=email,
                documento=documento,
                nombre=str(datos["nombre"]).strip(),
                apellido=str(datos["apellido"]).strip(),
                telefono=str(datos.get("telefono") or "").strip(),
                id_rol=rol,
                estado=True,
                intentos_fallidos=0,
                debe_cambiar_password=True,
                contrasena_temporal_expira=expira,
            )
            usuario.set_password(clave)
            usuario.save(update_fields=["password"])
            self._reemplazar_sedes(usuario, sedes)
            despues = snapshot_usuario(usuario)
            self._auditar(ctx, "CREAR_USUARIO", usuario.id_usuario, None, despues)
        if self._email:
            try:
                self._email.enviar_contrasena_inicial(email, nombre_completo(usuario), clave)
            except Exception:
                logger.exception("No se pudo enviar correo de contrasena inicial")
        return MSG_USUARIO_CREADO, self._detalle(usuario)

    def _actualizar(self, ctx: AuthContext, id_usuario: int, datos: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        version = int(datos.get("version_fila") or 0)
        self._validar_obligatorios_edicion(datos)
        email = str(datos["email"]).strip()
        documento = str(datos["documento"]).strip()
        if not correo_valido(email):
            raise ReglaNegocioError(MSG_EMAIL_INVALIDO, codigo="EMAIL_INVALIDO")
        exigir_documento(documento)
        exigir_telefono(str(datos.get("telefono") or ""))
        if Usuarios.objects.filter(email__iexact=email).exclude(pk=id_usuario).exists():
            raise ReglaNegocioError(MSG_EMAIL_DUPLICADO, codigo="EMAIL_DUPLICADO")
        if Usuarios.objects.filter(documento=documento).exclude(pk=id_usuario).exists():
            raise ReglaNegocioError(MSG_DOCUMENTO_DUPLICADO, codigo="DOCUMENTO_DUPLICADO")
        rol = self._rol_activo(int(datos["id_rol"]))
        sedes = _sedes_payload(datos.get("sedes"))
        self._validar_sedes(sedes)
        with transaction.atomic():
            usuario = Usuarios.objects.select_for_update().select_related("id_rol").get(pk=id_usuario)
            if int(usuario.version_fila) != version:
                raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
            antes = snapshot_usuario(usuario)
            usuario.nombre = str(datos["nombre"]).strip()
            usuario.apellido = str(datos["apellido"]).strip()
            usuario.telefono = str(datos.get("telefono") or "").strip()
            usuario.email = email
            usuario.documento = documento
            usuario.id_rol = rol
            usuario.version_fila = int(usuario.version_fila) + 1
            usuario.save(
                update_fields=[
                    "nombre",
                    "apellido",
                    "telefono",
                    "email",
                    "documento",
                    "id_rol",
                    "version_fila",
                    "fecha_actualizacion",
                ]
            )
            self._reemplazar_sedes(usuario, sedes)
            despues = snapshot_usuario(usuario)
            self._auditar(ctx, "EDITAR_USUARIO", usuario.id_usuario, antes, despues)
        return MSG_USUARIO_ACTUALIZADO, self._detalle(usuario)

    def _cambiar_estado(self, ctx: AuthContext, id_usuario: int, accion: str) -> str:
        accion = (accion or "").strip().lower()
        if accion not in {"activar", "desactivar", "bloquear"}:
            raise ReglaNegocioError(MSG_ESTADO_ERROR, codigo="ACCION_INVALIDA")
        horas = int(getattr(settings, "BLOQUEO_MANUAL_HORAS", 24))
        with transaction.atomic():
            usuario = Usuarios.objects.select_for_update().select_related("id_rol").get(pk=id_usuario)
            antes = snapshot_usuario(usuario)
            if accion == "desactivar":
                usuario.estado = False
                self._sessions.revocar_usuario(usuario.id_usuario)
            elif accion == "activar":
                usuario.estado = True
                usuario.bloqueado_hasta = None
                usuario.intentos_fallidos = 0
            else:
                usuario.bloqueado_hasta = timezone.now() + timedelta(hours=horas)
                self._sessions.revocar_usuario(usuario.id_usuario)
            usuario.version_fila = int(usuario.version_fila) + 1
            usuario.save(
                update_fields=["estado", "bloqueado_hasta", "intentos_fallidos", "version_fila", "fecha_actualizacion"]
            )
            despues = snapshot_usuario(usuario)
            self._auditar(ctx, "CAMBIAR_ESTADO_USUARIO", usuario.id_usuario, antes, despues)
        return MSG_ESTADO_ACTUALIZADO

    def _generar_contrasena_temporal(self, ctx: AuthContext, id_usuario: int) -> tuple[str, str]:
        clave = generar_contrasena_inicial(12)
        expira = timezone.now() + timedelta(hours=24)
        with transaction.atomic():
            usuario = Usuarios.objects.select_for_update().get(pk=id_usuario)
            antes = snapshot_usuario(usuario, incluir_sedes=False)
            usuario.set_password(clave)
            usuario.debe_cambiar_password = True
            usuario.contrasena_temporal_expira = expira
            usuario.credential_version = int(usuario.credential_version or 1) + 1
            usuario.version_fila = int(usuario.version_fila) + 1
            usuario.save(
                update_fields=[
                    "password",
                    "debe_cambiar_password",
                    "contrasena_temporal_expira",
                    "credential_version",
                    "version_fila",
                    "fecha_actualizacion",
                ]
            )
            despues = snapshot_usuario(usuario, incluir_sedes=False)
            despues.pop("password_hash", None)
            self._auditar(ctx, "CONTRASENA_TEMPORAL", usuario.id_usuario, antes, despues)
            self._sessions.revocar_usuario(usuario.id_usuario)
        return MSG_CONTRASENA_TEMP_OK, clave

    def _validar_obligatorios_creacion(self, datos: dict[str, Any]) -> None:
        for campo in ("nombre", "apellido", "documento", "email", "id_rol"):
            if not str(datos.get(campo) or "").strip():
                raise ReglaNegocioError(MSG_CAMPOS_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")

    def _validar_obligatorios_edicion(self, datos: dict[str, Any]) -> None:
        self._validar_obligatorios_creacion(datos)

    def _rol_activo(self, id_rol: int) -> Roles:
        try:
            rol = Roles.objects.get(pk=id_rol, estado=True)
        except Roles.DoesNotExist as err:
            raise ReglaNegocioError(MSG_ROL_INACTIVO, codigo="ROL_INVALIDO") from err
        return rol

    def _validar_sedes(self, sedes: list[dict[str, Any]]) -> None:
        if not sedes:
            raise ReglaNegocioError(MSG_SEDE_OBLIGATORIA, codigo="SEDE_OBLIGATORIA")
        principales = [s for s in sedes if s["es_principal"]]
        if len(principales) != 1:
            raise ReglaNegocioError(MSG_SEDE_OBLIGATORIA, codigo="SEDE_PRINCIPAL")
        ids = {s["id_sede"] for s in sedes}
        activas = Sedes.objects.filter(id_sede__in=ids, estado=True).count()
        if activas != len(ids):
            raise ReglaNegocioError(MSG_SEDE_OBLIGATORIA, codigo="SEDE_INACTIVA")

    def _reemplazar_sedes(self, usuario: Usuarios, sedes: list[dict[str, Any]]) -> None:
        Usuario_sede.objects.filter(id_usuario=usuario).delete()
        Usuario_sede.objects.bulk_create(
            [
                Usuario_sede(
                    id_usuario=usuario,
                    id_sede_id=s["id_sede"],
                    es_principal=s["es_principal"],
                    estado=True,
                )
                for s in sedes
            ]
        )

    def _fila_listado(self, usuario: Usuarios) -> dict[str, Any]:
        sede_principal = (
            Usuario_sede.objects.filter(id_usuario=usuario, es_principal=True, estado=True)
            .select_related("id_sede")
            .first()
        )
        sede_nombre = sede_principal.id_sede.nombre if sede_principal else ""
        return {
            "id_usuario": usuario.id_usuario,
            "nombre_completo": nombre_completo(usuario),
            "documento": usuario.documento,
            "email": usuario.email,
            "rol": usuario.id_rol.nombre,
            "estado": estado_etiqueta(usuario),
            "ultimo_acceso": usuario.ultimo_acceso,
            "sede_principal": sede_nombre,
        }

    def _detalle(self, usuario: Usuarios) -> dict[str, Any]:
        base = snapshot_usuario(usuario)
        base["nombre_completo"] = nombre_completo(usuario)
        base["acciones_estado"] = self._acciones_estado(usuario)
        base["puede_contrasena_temporal"] = True
        return base

    def _acciones_estado(self, usuario: Usuarios) -> list[str]:
        etiqueta = estado_etiqueta(usuario)
        if etiqueta == "Activo":
            return ["desactivar", "bloquear"]
        if etiqueta == "Inactivo":
            return ["activar"]
        return ["activar", "desactivar"]

    def _auditar(
        self,
        ctx: AuthContext,
        accion: str,
        id_entidad: int,
        antes: dict[str, Any] | None,
        despues: dict[str, Any] | None,
    ) -> None:
        if not self._audit:
            return
        self._audit.registrar(
            AuditoriaDTO(
                id_usuario=ctx.id_usuario,
                accion=accion,
                entidad="Usuarios",
                id_entidad=id_entidad,
                datos_antes=antes,
                datos_despues=despues,
                motivo=accion,
                id_correlacion=ctx.id_correlacion,
                ip=ctx.ip,
                user_agent=ctx.user_agent,
            )
        )


class PerfilPropioService:
    def __init__(self, audit_port: AuditPort | None = None) -> None:
        self._audit = audit_port

    def actualizar(self, ctx: AuthContext, usuario: Usuarios, datos: dict[str, Any]) -> str:
        if datos.get("id_rol") is not None or datos.get("rol_nombre"):
            raise ReglaNegocioError(MSG_ROL_PROPIO, codigo="ROL_PROPIO")
        nombre = str(datos.get("nombre") or "").strip()
        apellido = str(datos.get("apellido") or "").strip()
        if not nombre or not apellido:
            raise ReglaNegocioError(MSG_CAMPOS_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        telefono = str(datos.get("telefono") or "").strip()
        exigir_telefono(telefono)
        try:
            with transaction.atomic():
                bloqueado = Usuarios.objects.select_for_update().get(pk=usuario.pk)
                antes = snapshot_usuario(bloqueado, incluir_sedes=False)
                bloqueado.nombre = nombre
                bloqueado.apellido = apellido
                bloqueado.telefono = telefono
                bloqueado.version_fila = int(bloqueado.version_fila) + 1
                bloqueado.save(update_fields=["nombre", "apellido", "telefono", "version_fila", "fecha_actualizacion"])
                despues = snapshot_usuario(bloqueado, incluir_sedes=False)
                if self._audit:
                    self._audit.registrar(
                        AuditoriaDTO(
                            id_usuario=ctx.id_usuario,
                            accion="EDITAR_PERFIL",
                            entidad="Usuarios",
                            id_entidad=bloqueado.id_usuario,
                            datos_antes=antes,
                            datos_despues=despues,
                            motivo="Edicion de perfil propio",
                            id_correlacion=ctx.id_correlacion,
                            ip=ctx.ip,
                            user_agent=ctx.user_agent,
                        )
                    )
            return MSG_PERFIL_ACTUALIZADO
        except ReglaNegocioError:
            raise
        except Exception as exc:
            logger.exception("Fallo al actualizar perfil")
            raise DominioError(MSG_PERFIL_ERROR, codigo="ERROR_PERFIL") from exc
