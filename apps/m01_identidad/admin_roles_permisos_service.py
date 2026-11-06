# Epic 3 — Roles, permisos y matriz (HU 13–17)
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.db.models import Q

from apps.m01_identidad.mensajes import (
    MSG_CONCURRENCIA,
    MSG_LISTADO_PERMISOS,
    MSG_LISTADO_ROLES,
    MSG_LISTADO_ROLES_VACIO,
    MSG_MATRIZ_DESTINO,
    MSG_MATRIZ_ERROR,
    MSG_MATRIZ_GUARDADA,
    MSG_PERMISO_ACTUALIZADO,
    MSG_PERMISO_ACTUALIZAR_ERROR,
    MSG_PERMISO_CAMPOS,
    MSG_PERMISO_CREADO,
    MSG_PERMISO_CREAR_ERROR,
    MSG_PERMISO_DUPLICADO,
    MSG_PERMISO_INACTIVADO,
    MSG_ROL_ACTUALIZADO,
    MSG_ROL_ACTUALIZAR_ERROR,
    MSG_ROL_BASE_PROTEGIDO,
    MSG_ROL_CREADO,
    MSG_ROL_CREAR_ERROR,
    MSG_ROL_ELIMINADO,
    MSG_ROL_ELIMINAR_ASIGNADO,
    MSG_ROL_ELIMINAR_ERROR,
    MSG_ROL_INACTIVAR_USUARIOS,
    MSG_ROL_NOMBRE_DUPLICADO,
    MSG_ROL_NOMBRE_OBLIGATORIO,
)
from apps.m01_identidad.models import Permisos, Rol_permiso, Roles, Usuario_permiso, Usuarios
from apps.m01_identidad.panel_accesos import ACCIONES_CATALOGO, MODULOS_CATALOGO
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import DominioError, ReglaNegocioError
from contratos.puertos.auditoria import AuditPort

logger = logging.getLogger(__name__)


def _snapshot_rol(rol: Roles) -> dict[str, Any]:
    return {
        "id_rol": rol.id_rol,
        "nombre": rol.nombre,
        "descripcion": rol.descripcion,
        "estado": rol.estado,
        "es_rol_base": rol.es_rol_base,
        "version_fila": rol.version_fila,
    }


def _snapshot_permiso(p: Permisos) -> dict[str, Any]:
    return {
        "id_permiso": p.id_permiso,
        "nombre": p.nombre,
        "modulo": p.modulo,
        "accion": p.accion,
        "descripcion": p.descripcion,
        "estado": p.estado,
        "version_fila": p.version_fila,
    }


@dataclass(frozen=True)
class Pagina:
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    mensaje: str


class AdminRolesPermisosService:
    def __init__(self, audit_port: AuditPort | None = None) -> None:
        self._audit = audit_port

    def listar_roles(self, q: str, estado_filtro: str, page: int, page_size: int) -> Pagina:
        qs = Roles.objects.all().order_by("nombre")
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(Q(nombre__icontains=texto) | Q(descripcion__icontains=texto))
        if estado_filtro == "activo":
            qs = qs.filter(estado=True)
        elif estado_filtro == "inactivo":
            qs = qs.filter(estado=False)
        total = qs.count()
        offset = max(0, (page - 1) * page_size)
        filas = qs[offset : offset + page_size]
        items = [
            {
                "id_rol": r.id_rol,
                "nombre": r.nombre,
                "descripcion": r.descripcion,
                "estado": r.estado,
                "es_rol_base": r.es_rol_base,
                "version_fila": r.version_fila,
            }
            for r in filas
        ]
        mensaje = (
            MSG_LISTADO_ROLES_VACIO
            if total == 0
            else MSG_LISTADO_ROLES.format(n=len(items), total=total)
        )
        return Pagina(items=items, total=total, page=page, page_size=page_size, mensaje=mensaje)

    def crear_rol(self, ctx: AuthContext, datos: dict[str, Any]) -> tuple[dict[str, Any], str]:
        nombre = str(datos.get("nombre") or "").strip()
        if not nombre:
            raise ReglaNegocioError(MSG_ROL_NOMBRE_OBLIGATORIO, codigo="ROL_NOMBRE_OBLIGATORIO")
        if len(nombre) > 30:
            raise ReglaNegocioError(MSG_ROL_NOMBRE_OBLIGATORIO, codigo="ROL_NOMBRE_LARGO")
        if Roles.objects.filter(nombre__iexact=nombre).exists():
            raise ReglaNegocioError(MSG_ROL_NOMBRE_DUPLICADO, codigo="ROL_NOMBRE_DUPLICADO")
        descripcion = str(datos.get("descripcion") or "").strip()
        try:
            with transaction.atomic():
                rol = Roles.objects.create(
                    nombre=nombre,
                    descripcion=descripcion,
                    estado=True,
                    es_rol_base=False,
                )
                self._auditar(ctx, "CREAR_ROL", "Roles", rol.id_rol, None, _snapshot_rol(rol))
            return _snapshot_rol(rol), MSG_ROL_CREADO
        except ReglaNegocioError:
            raise
        except Exception:
            logger.exception("crear_rol")
            raise DominioError(MSG_ROL_CREAR_ERROR, codigo="ROL_CREAR_ERROR") from None

    def detalle_rol(self, id_rol: int) -> dict[str, Any]:
        rol = Roles.objects.get(pk=id_rol)
        return _snapshot_rol(rol)

    def eliminar_rol(self, ctx: AuthContext, id_rol: int) -> str:
        try:
            with transaction.atomic():
                rol = Roles.objects.select_for_update().get(pk=id_rol)
                if rol.es_rol_base:
                    raise ReglaNegocioError(MSG_ROL_BASE_PROTEGIDO, codigo="ROL_BASE_PROTEGIDO")
                if Usuarios.objects.filter(id_rol=rol).exists():
                    raise ReglaNegocioError(
                        MSG_ROL_ELIMINAR_ASIGNADO, codigo="ROL_USUARIOS_ASIGNADOS"
                    )
                antes = _snapshot_rol(rol)
                id_ent = rol.id_rol
                Rol_permiso.objects.filter(id_rol=rol).delete()
                rol.delete()
                self._auditar(ctx, "ELIMINAR_ROL", "Roles", id_ent, antes, None)
            return MSG_ROL_ELIMINADO
        except ReglaNegocioError:
            raise
        except Roles.DoesNotExist:
            raise
        except Exception:
            logger.exception("eliminar_rol")
            raise DominioError(MSG_ROL_ELIMINAR_ERROR, codigo="ROL_ELIMINAR_ERROR") from None

    def editar_rol(
        self, ctx: AuthContext, id_rol: int, datos: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        version = int(datos.get("version_fila") or 0)
        try:
            with transaction.atomic():
                rol = Roles.objects.select_for_update().get(pk=id_rol)
                if rol.es_rol_base and (
                    datos.get("nombre") is not None or datos.get("estado") is False
                ):
                    raise ReglaNegocioError(MSG_ROL_BASE_PROTEGIDO, codigo="ROL_BASE_PROTEGIDO")
                if int(rol.version_fila) != version:
                    raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
                antes = _snapshot_rol(rol)
                if not rol.es_rol_base and datos.get("nombre") is not None:
                    nombre = str(datos["nombre"]).strip()
                    if not nombre:
                        raise ReglaNegocioError(
                            MSG_ROL_NOMBRE_OBLIGATORIO, codigo="ROL_NOMBRE_OBLIGATORIO"
                        )
                    if Roles.objects.filter(nombre__iexact=nombre).exclude(pk=rol.pk).exists():
                        raise ReglaNegocioError(
                            MSG_ROL_NOMBRE_DUPLICADO, codigo="ROL_NOMBRE_DUPLICADO"
                        )
                    rol.nombre = nombre
                if datos.get("descripcion") is not None:
                    rol.descripcion = str(datos["descripcion"] or "").strip()
                if datos.get("estado") is not None and not rol.es_rol_base:
                    nuevo_estado = bool(datos["estado"])
                    if (
                        not nuevo_estado
                        and Usuarios.objects.filter(id_rol=rol, estado=True).exists()
                    ):
                        raise ReglaNegocioError(
                            MSG_ROL_INACTIVAR_USUARIOS, codigo="ROL_USUARIOS_ACTIVOS"
                        )
                    rol.estado = nuevo_estado
                rol.version_fila = int(rol.version_fila) + 1
                rol.save()
                despues = _snapshot_rol(rol)
                self._auditar(ctx, "EDITAR_ROL", "Roles", rol.id_rol, antes, despues)
            return despues, MSG_ROL_ACTUALIZADO
        except (ReglaNegocioError, Roles.DoesNotExist):
            raise
        except Exception:
            logger.exception("editar_rol")
            raise DominioError(MSG_ROL_ACTUALIZAR_ERROR, codigo="ROL_ACTUALIZAR_ERROR") from None

    def listar_permisos(
        self, q: str, modulo: str, accion: str, estado_filtro: str, page: int, page_size: int
    ) -> Pagina:
        qs = Permisos.objects.all().order_by("modulo", "accion")
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(nombre__icontains=texto) | Q(modulo__icontains=texto) | Q(accion__icontains=texto)
            )
        if modulo:
            qs = qs.filter(modulo=modulo)
        if accion:
            qs = qs.filter(accion=accion)
        if estado_filtro == "activo":
            qs = qs.filter(estado=True)
        elif estado_filtro == "inactivo":
            qs = qs.filter(estado=False)
        total = qs.count()
        offset = max(0, (page - 1) * page_size)
        items = [_snapshot_permiso(p) for p in qs[offset : offset + page_size]]
        mensaje = MSG_LISTADO_PERMISOS.format(n=len(items), total=total)
        return Pagina(items=items, total=total, page=page, page_size=page_size, mensaje=mensaje)

    def crear_permiso(self, ctx: AuthContext, datos: dict[str, Any]) -> tuple[dict[str, Any], str]:
        nombre = str(datos.get("nombre") or "").strip()
        modulo = str(datos.get("modulo") or "").strip()
        accion = str(datos.get("accion") or "").strip()
        if not nombre or not modulo or not accion:
            raise ReglaNegocioError(MSG_PERMISO_CAMPOS, codigo="PERMISO_CAMPOS")
        if Permisos.objects.filter(modulo=modulo, accion=accion).exists():
            raise ReglaNegocioError(MSG_PERMISO_DUPLICADO, codigo="PERMISO_DUPLICADO")
        descripcion = str(datos.get("descripcion") or "").strip()
        try:
            with transaction.atomic():
                perm = Permisos.objects.create(
                    nombre=nombre[:100],
                    modulo=modulo,
                    accion=accion,
                    descripcion=descripcion,
                    estado=True,
                )
                self._auditar(
                    ctx, "CREAR_PERMISO", "Permisos", perm.id_permiso, None, _snapshot_permiso(perm)
                )
            return _snapshot_permiso(perm), MSG_PERMISO_CREADO
        except ReglaNegocioError:
            raise
        except Exception:
            logger.exception("crear_permiso")
            raise DominioError(MSG_PERMISO_CREAR_ERROR, codigo="PERMISO_CREAR_ERROR") from None

    def editar_permiso(
        self, ctx: AuthContext, id_permiso: int, datos: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        version = int(datos.get("version_fila") or 0)
        try:
            with transaction.atomic():
                perm = Permisos.objects.select_for_update().get(pk=id_permiso)
                if int(perm.version_fila) != version:
                    raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
                antes = _snapshot_permiso(perm)
                if datos.get("nombre") is not None:
                    nombre = str(datos["nombre"]).strip()
                    if not nombre:
                        raise ReglaNegocioError(MSG_PERMISO_CAMPOS, codigo="PERMISO_CAMPOS")
                    perm.nombre = nombre[:100]
                if datos.get("modulo") is not None:
                    perm.modulo = str(datos["modulo"]).strip()
                if datos.get("accion") is not None:
                    perm.accion = str(datos["accion"]).strip()
                if datos.get("descripcion") is not None:
                    perm.descripcion = str(datos["descripcion"] or "").strip()
                if perm.modulo and perm.accion:
                    dup = Permisos.objects.filter(modulo=perm.modulo, accion=perm.accion).exclude(
                        pk=perm.pk
                    )
                    if dup.exists():
                        raise ReglaNegocioError(MSG_PERMISO_DUPLICADO, codigo="PERMISO_DUPLICADO")
                msg_extra = ""
                if datos.get("estado") is not None:
                    perm.estado = bool(datos["estado"])
                    if not perm.estado:
                        msg_extra = MSG_PERMISO_INACTIVADO
                perm.version_fila = int(perm.version_fila) + 1
                perm.save()
                despues = _snapshot_permiso(perm)
                self._auditar(ctx, "EDITAR_PERMISO", "Permisos", perm.id_permiso, antes, despues)
            mensaje = msg_extra or MSG_PERMISO_ACTUALIZADO
            return despues, mensaje
        except (ReglaNegocioError, Permisos.DoesNotExist):
            raise
        except Exception:
            logger.exception("editar_permiso")
            raise DominioError(
                MSG_PERMISO_ACTUALIZAR_ERROR, codigo="PERMISO_ACTUALIZAR_ERROR"
            ) from None

    def catalogos(self) -> dict[str, Any]:
        return {"modulos": MODULOS_CATALOGO, "acciones": ACCIONES_CATALOGO}

    def obtener_matriz(self, tipo: str, id_destino: int) -> dict[str, Any]:
        permisos = Permisos.objects.filter(estado=True).order_by("modulo", "accion")
        filas: list[dict[str, Any]] = []
        if tipo == "rol":
            rol = Roles.objects.get(pk=id_destino, estado=True)
            asignados = {
                rp.id_permiso_id: rp.permitido
                for rp in Rol_permiso.objects.filter(id_rol=rol).select_related("id_permiso")
            }
            for p in permisos:
                filas.append(
                    {
                        "id_permiso": p.id_permiso,
                        "modulo": p.modulo,
                        "accion": p.accion,
                        "nombre": p.nombre or f"{p.modulo}:{p.accion}",
                        "asignado": p.id_permiso in asignados,
                        "permitido": asignados.get(p.id_permiso),
                        "heredado_de_rol": None,
                    }
                )
            return {
                "tipo": "rol",
                "id_destino": rol.id_rol,
                "nombre_destino": rol.nombre,
                "filas": filas,
            }
        if tipo == "usuario":
            usuario = Usuarios.objects.select_related("id_rol").get(pk=id_destino, estado=True)
            rol_perms = {
                rp.id_permiso_id: rp.permitido
                for rp in Rol_permiso.objects.filter(
                    id_rol=usuario.id_rol, permitido=True
                ).select_related("id_permiso")
            }
            overrides = {
                up.id_permiso_id: up.permitido
                for up in Usuario_permiso.objects.filter(id_usuario=usuario).select_related(
                    "id_permiso"
                )
            }
            for p in permisos:
                heredado = rol_perms.get(p.id_permiso)
                override = overrides.get(p.id_permiso)
                filas.append(
                    {
                        "id_permiso": p.id_permiso,
                        "modulo": p.modulo,
                        "accion": p.accion,
                        "nombre": p.nombre or f"{p.modulo}:{p.accion}",
                        "asignado": override is not None or heredado is True,
                        "permitido": override if override is not None else heredado,
                        "heredado_de_rol": heredado if override is not None else None,
                        "tiene_excepcion": override is not None,
                    }
                )
            return {
                "tipo": "usuario",
                "id_destino": usuario.id_usuario,
                "nombre_destino": f"{usuario.nombre} {usuario.apellido}".strip(),
                "filas": filas,
            }
        raise ReglaNegocioError(MSG_MATRIZ_DESTINO, codigo="MATRIZ_DESTINO")

    def guardar_matriz(self, ctx: AuthContext, datos: dict[str, Any]) -> str:
        tipo = str(datos.get("tipo") or "").strip().lower()
        id_destino = int(datos.get("id_destino") or 0)
        cambios = datos.get("cambios") or []
        if tipo not in ("rol", "usuario") or not id_destino:
            raise ReglaNegocioError(MSG_MATRIZ_DESTINO, codigo="MATRIZ_DESTINO")
        try:
            with transaction.atomic():
                prev = self.obtener_matriz(tipo, id_destino)
                antes: dict[str, Any] = {
                    "tipo": tipo,
                    "id_destino": id_destino,
                    "cambios": [
                        {
                            "id_permiso": f["id_permiso"],
                            "modulo": f["modulo"],
                            "accion": f["accion"],
                            "permitido": f.get("permitido"),
                        }
                        for f in prev["filas"]
                        if f.get("permitido") is not None
                    ],
                }
                despues: dict[str, Any] = {
                    "tipo": tipo,
                    "id_destino": id_destino,
                    "cambios": list(cambios),
                }
                if tipo == "rol":
                    rol = Roles.objects.select_for_update().get(pk=id_destino)
                    for item in cambios:
                        id_perm = int(item["id_permiso"])
                        permitido = bool(item.get("permitido"))
                        rp, created = Rol_permiso.objects.get_or_create(
                            id_rol=rol, id_permiso_id=id_perm, defaults={"permitido": permitido}
                        )
                        if not created:
                            rp.permitido = permitido
                            rp.save(update_fields=["permitido"])
                    entidad, id_ent = "Roles", rol.id_rol
                else:
                    usuario = Usuarios.objects.select_for_update().get(pk=id_destino)
                    for item in cambios:
                        id_perm = int(item["id_permiso"])
                        permitido = bool(item.get("permitido"))
                        if item.get("eliminar_excepcion"):
                            Usuario_permiso.objects.filter(
                                id_usuario=usuario, id_permiso_id=id_perm
                            ).delete()
                            continue
                        up, created = Usuario_permiso.objects.get_or_create(
                            id_usuario=usuario,
                            id_permiso_id=id_perm,
                            defaults={"permitido": permitido},
                        )
                        if not created:
                            up.permitido = permitido
                            up.save(update_fields=["permitido"])
                    usuario.credential_version = int(usuario.credential_version) + 1
                    usuario.save(update_fields=["credential_version"])
                    entidad, id_ent = "Usuarios", usuario.id_usuario
                self._auditar(ctx, "MATRIZ_PERMISOS", entidad, id_ent, antes, despues)
            return MSG_MATRIZ_GUARDADA
        except ReglaNegocioError:
            raise
        except Exception:
            logger.exception("guardar_matriz")
            raise DominioError(MSG_MATRIZ_ERROR, codigo="MATRIZ_ERROR") from None

    def _auditar(
        self,
        ctx: AuthContext,
        accion: str,
        entidad: str,
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
                entidad=entidad,
                id_entidad=id_entidad,
                datos_antes=antes,
                datos_despues=despues,
                motivo=accion,
                id_correlacion=ctx.id_correlacion,
                ip=ctx.ip,
                user_agent=ctx.user_agent,
            )
        )
