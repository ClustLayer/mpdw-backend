"""Backoffice directorio de proveedores (Épica 14)."""

from __future__ import annotations

import re
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.m01_identidad.models import Usuarios
from apps.m10_auditoria.services import AuditService
from apps.m14_proveedores.mensajes import (
    MSG_ACTUALIZADO,
    MSG_ACTUALIZAR_ERROR,
    MSG_CONCURRENCIA,
    MSG_CORREO,
    MSG_CREADO,
    MSG_CREAR_ERROR,
    MSG_DOCUMENTO_DUP,
    MSG_LISTADO,
    MSG_OBLIGATORIOS,
    MSG_SIN_COINCIDENCIAS,
    MSG_TELEFONO,
    MSG_TIPO_DOC,
)
from apps.m14_proveedores.models import TIPOS_DOCUMENTO, Proveedores
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ReglaNegocioError

E164_RE = re.compile(r"^\+?[1-9]\d{6,14}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TIPOS_VALIDOS = {c[0] for c in TIPOS_DOCUMENTO}


def _validar_e164(valor: str) -> str:
    t = (valor or "").strip()
    if not t:
        return ""
    if not E164_RE.match(t):
        raise ReglaNegocioError(MSG_TELEFONO, codigo="FORMATO_TELEFONO")
    return t if t.startswith("+") else f"+{t}"


def _validar_correo(valor: str) -> str:
    t = (valor or "").strip()
    if not t:
        return ""
    if not EMAIL_RE.match(t):
        raise ReglaNegocioError(MSG_CORREO, codigo="FORMATO_CORREO")
    return t


def _serializar(p: Proveedores) -> dict[str, Any]:
    return {
        "id_proveedor": p.id_proveedor,
        "nombre": p.nombre,
        "tipo_documento": p.tipo_documento,
        "numero_documento": p.numero_documento,
        "contacto_nombre": p.contacto_nombre,
        "contacto_cargo": p.contacto_cargo,
        "telefono": p.telefono,
        "correo": p.correo,
        "direccion": p.direccion,
        "ciudad": p.ciudad,
        "descripcion": p.descripcion,
        "productos_suministra": p.productos_suministra,
        "estado": p.estado,
        "version_fila": p.version_fila,
        "fecha_registro": p.fecha_registro.isoformat() if p.fecha_registro else None,
    }


def _usuario_id(ctx: AuthContext) -> int | None:
    if not ctx.id_usuario:  # pragma: no cover
        return None
    return ctx.id_usuario if Usuarios.objects.filter(pk=ctx.id_usuario).exists() else None


def _auditar(
    ctx: AuthContext,
    accion: str,
    entidad_id: int,
    antes: dict | None,
    despues: dict | None,
    audit: AuditService,
) -> None:
    audit.registrar(
        AuditoriaDTO(
            id_usuario=_usuario_id(ctx),
            accion=accion,
            entidad="Proveedores",
            id_entidad=entidad_id,
            datos_antes=antes,
            datos_despues=despues,
            motivo=accion,
            id_correlacion=ctx.id_correlacion,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    )


class AdminProveedoresService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()

    def listar(self, q: str, estado: str | None, page: int, page_size: int) -> dict[str, Any]:
        qs = Proveedores.objects.all()
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(nombre__icontains=texto)
                | Q(numero_documento__icontains=texto)
                | Q(contacto_nombre__icontains=texto)
                | Q(correo__icontains=texto)
                | Q(ciudad__icontains=texto)
            )
        est = (estado or "todos").lower()
        if est == "activo":
            qs = qs.filter(estado=True)
        elif est == "inactivo":
            qs = qs.filter(estado=False)
        total = qs.count()
        if total == 0 and texto:
            return {"items": [], "total": 0, "mensaje": MSG_SIN_COINCIDENCIAS, "page": page, "page_size": page_size}
        offset = max(0, (max(1, page) - 1) * page_size)
        filas = [_serializar(p) for p in qs.order_by("nombre")[offset : offset + page_size]]
        return {
            "items": filas,
            "total": total,
            "mensaje": MSG_LISTADO.format(n=len(filas), total=total),
            "page": page,
            "page_size": page_size,
        }

    def obtener(self, pk: int) -> dict[str, Any]:
        p = Proveedores.objects.get(pk=pk)
        return _serializar(p)

    def activos(self) -> dict[str, Any]:
        items = [
            {
                "id_proveedor": p.id_proveedor,
                "nombre": p.nombre,
                "numero_documento": p.numero_documento,
            }
            for p in Proveedores.objects.filter(estado=True).order_by("nombre")
        ]
        return {"items": items}

    def _validar_payload(self, datos: dict[str, Any], *, crear: bool) -> dict[str, Any]:
        nombre = (datos.get("nombre") or "").strip()
        if not nombre:
            raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        tipo_doc = (datos.get("tipo_documento") or "").strip()
        if not tipo_doc or tipo_doc not in TIPOS_VALIDOS:
            raise ReglaNegocioError(MSG_TIPO_DOC if tipo_doc else MSG_OBLIGATORIOS, codigo="TIPO_DOCUMENTO")
        telefono = _validar_e164(str(datos.get("telefono") or ""))
        correo = _validar_correo(str(datos.get("correo") or ""))
        payload = {
            "nombre": nombre[:255],
            "tipo_documento": tipo_doc,
            "numero_documento": (datos.get("numero_documento") or "").strip()[:30],
            "contacto_nombre": (datos.get("contacto_nombre") or "").strip()[:255],
            "contacto_cargo": (datos.get("contacto_cargo") or "").strip()[:120],
            "telefono": telefono,
            "correo": correo,
            "direccion": (datos.get("direccion") or "").strip()[:255],
            "ciudad": (datos.get("ciudad") or "").strip()[:100],
            "descripcion": (datos.get("descripcion") or "").strip(),
            "productos_suministra": (datos.get("productos_suministra") or "").strip(),
        }
        if not crear:
            payload["estado"] = bool(datos.get("estado", True))
        return payload

    def _verificar_documento(self, documento: str, excluir_id: int | None = None) -> None:
        doc = (documento or "").strip()
        if not doc:
            return
        qs = Proveedores.objects.filter(numero_documento=doc)
        if excluir_id:
            qs = qs.exclude(pk=excluir_id)
        if qs.exists():
            raise ReglaNegocioError(MSG_DOCUMENTO_DUP, codigo="DOCUMENTO_DUP")

    def crear(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        norm = self._validar_payload(datos, crear=True)
        self._verificar_documento(norm["numero_documento"])
        try:
            with transaction.atomic():
                p = Proveedores.objects.create(**norm, estado=True)
                _auditar(ctx, "CREAR", p.id_proveedor, None, _serializar(p), self._audit)
        except IntegrityError as exc:
            raise ReglaNegocioError(MSG_DOCUMENTO_DUP, codigo="DOCUMENTO_DUP") from exc
        except Exception as exc:  # pragma: no cover
            raise ReglaNegocioError(MSG_CREAR_ERROR, codigo="ERROR_INTERNO") from exc
        return {"mensaje": MSG_CREADO, "proveedor": _serializar(p)}

    def actualizar(self, ctx: AuthContext, pk: int, datos: dict[str, Any]) -> dict[str, Any]:
        try:
            p = Proveedores.objects.get(pk=pk)
        except Proveedores.DoesNotExist as exc:
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="NO_ENCONTRADO") from exc
        version = int(datos.get("version_fila") or 0)
        if version != p.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        norm = self._validar_payload(datos, crear=False)
        self._verificar_documento(norm["numero_documento"], excluir_id=pk)
        antes = _serializar(p)
        norm["estado"] = bool(datos.get("estado", p.estado))
        try:
            with transaction.atomic():
                for k, v in norm.items():
                    setattr(p, k, v)
                p.version_fila = int(p.version_fila) + 1
                p.save()
                _auditar(ctx, "EDITAR", p.id_proveedor, antes, _serializar(p), self._audit)
        except IntegrityError as exc:
            raise ReglaNegocioError(MSG_DOCUMENTO_DUP, codigo="DOCUMENTO_DUP") from exc
        except Exception as exc:  # pragma: no cover
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="ERROR_INTERNO") from exc
        return {"mensaje": MSG_ACTUALIZADO, "proveedor": _serializar(p)}
