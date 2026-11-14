"""Backoffice eventos y novedades (Épica 12)."""

from __future__ import annotations

import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from PIL import Image

from apps.m01_identidad.models import Usuarios
from apps.m02_sedes.models import Sedes
from apps.m10_auditoria.services import AuditService
from apps.m11_eventos.mensajes import (
    MSG_ACTUALIZADO,
    MSG_ACTUALIZAR_ERROR,
    MSG_ARCHIVO,
    MSG_CONCURRENCIA,
    MSG_CREADO,
    MSG_CREAR_ERROR,
    MSG_FECHAS,
    MSG_IMPACTO,
    MSG_LISTADO,
    MSG_OBLIGATORIOS,
    MSG_PUBLICOS,
    MSG_SIN_COINCIDENCIAS,
)
from apps.m11_eventos.models import IMPACTOS, Eventos_novedades
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ReglaNegocioError

IMPACTOS_VALIDOS = {c[0] for c in IMPACTOS}
MAX_IMAGEN = 5 * 1024 * 1024
MIME_OK = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MEDIA_RUTA = "/api/v1/catalogo/media"


def _imagen_publica(url: str) -> str:
    if not url or url.startswith(("http://", "https://", "/")):
        return url
    return f"{MEDIA_RUTA}/{url.lstrip('/')}"


def _parse_dt(valor: Any) -> datetime | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        dt = valor
    else:
        parsed = parse_datetime(str(valor))
        if parsed is None:
            try:
                parsed = datetime.fromisoformat(str(valor))
            except ValueError:
                return None
        dt = parsed
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _serializar(e: Eventos_novedades) -> dict[str, Any]:
    sede_nombre = e.id_sede.nombre if e.id_sede_id and e.id_sede else ""
    return {
        "id_evento": e.id_evento,
        "tipo": e.tipo,
        "titulo": e.titulo,
        "descripcion": e.descripcion,
        "fecha_inicio": e.fecha_inicio.isoformat() if e.fecha_inicio else None,
        "fecha_fin": e.fecha_fin.isoformat() if e.fecha_fin else None,
        "impacto": e.impacto,
        "areas_afectadas": e.areas_afectadas,
        "id_sede": e.id_sede_id,
        "sede_nombre": sede_nombre,
        "id_usuario": e.id_usuario_id,
        "estado": e.estado,
        "visible_sitio": e.visible_sitio,
        "imagen_url": e.imagen_url,
        "importancia_clave": e.importancia_clave,
        "version_fila": e.version_fila,
        "fecha_registro": e.fecha_registro.isoformat() if e.fecha_registro else None,
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
            entidad="Eventos_novedades",
            id_entidad=entidad_id,
            datos_antes=antes,
            datos_despues=despues,
            motivo=accion,
            id_correlacion=ctx.id_correlacion,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    )


class AdminEventosService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()

    def sedes_activas(self) -> dict[str, Any]:
        items = [
            {"id_sede": s.id_sede, "nombre": s.nombre}
            for s in Sedes.objects.filter(estado=True).order_by("nombre")
        ]
        return {"items": items}

    def listar(self, q: str, estado: str | None, page: int, page_size: int) -> dict[str, Any]:
        qs = Eventos_novedades.objects.select_related("id_sede")
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(titulo__icontains=texto)
                | Q(descripcion__icontains=texto)
                | Q(tipo__icontains=texto)
                | Q(areas_afectadas__icontains=texto)
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
        filas = [_serializar(e) for e in qs.order_by("-fecha_inicio")[offset : offset + page_size]]
        return {
            "items": filas,
            "total": total,
            "mensaje": MSG_LISTADO.format(n=len(filas), total=total),
            "page": page,
            "page_size": page_size,
        }

    def obtener(self, pk: int) -> dict[str, Any]:
        e = Eventos_novedades.objects.select_related("id_sede").get(pk=pk)
        return _serializar(e)

    def publicos(self) -> dict[str, Any]:
        qs = (
            Eventos_novedades.objects.filter(estado=True, visible_sitio=True)
            .select_related("id_sede")
            .order_by("-fecha_inicio")
        )
        items = []
        for e in qs[:50]:
            data = _serializar(e)
            data["imagen_url"] = _imagen_publica(data.get("imagen_url") or "")
            items.append(data)
        return {"items": items, "mensaje": MSG_PUBLICOS}

    def _validar_payload(self, datos: dict[str, Any], *, crear: bool) -> dict[str, Any]:
        titulo = (datos.get("titulo") or "").strip()
        descripcion = (datos.get("descripcion") or "").strip()
        tipo = (datos.get("tipo") or "").strip()
        if not titulo or not descripcion or not tipo:
            raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        inicio = _parse_dt(datos.get("fecha_inicio"))
        if not inicio:
            raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        fin = _parse_dt(datos.get("fecha_fin"))
        if fin and fin < inicio:
            raise ReglaNegocioError(MSG_FECHAS, codigo="FECHAS_INVALIDAS")
        impacto = (datos.get("impacto") or "Medio").strip()
        if impacto not in IMPACTOS_VALIDOS:
            raise ReglaNegocioError(MSG_IMPACTO, codigo="IMPACTO_INVALIDO")
        id_sede = datos.get("id_sede")
        id_sede_id = None
        if id_sede not in (None, "", 0, "0"):
            try:
                sid = int(id_sede)
            except (TypeError, ValueError) as exc:
                raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="SEDE_INVALIDA") from exc
            if not Sedes.objects.filter(pk=sid, estado=True).exists():
                raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="SEDE_INACTIVA")
            id_sede_id = sid
        payload = {
            "tipo": tipo[:50],
            "titulo": titulo[:150],
            "descripcion": descripcion,
            "fecha_inicio": inicio,
            "fecha_fin": fin,
            "impacto": impacto,
            "areas_afectadas": (datos.get("areas_afectadas") or "").strip(),
            "id_sede_id": id_sede_id,
            "visible_sitio": bool(datos.get("visible_sitio")),
            "imagen_url": (datos.get("imagen_url") or "").strip()[:500],
            "importancia_clave": bool(datos.get("importancia_clave")),
        }
        if not crear:
            payload["estado"] = bool(datos.get("estado", True))
        return payload

    def crear(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        norm = self._validar_payload(datos, crear=True)
        uid = _usuario_id(ctx)
        try:
            with transaction.atomic():
                e = Eventos_novedades.objects.create(**norm, estado=True, id_usuario_id=uid)
                _auditar(ctx, "CREAR", e.id_evento, None, _serializar(e), self._audit)
        except Exception as exc:  # pragma: no cover
            raise ReglaNegocioError(MSG_CREAR_ERROR, codigo="ERROR_INTERNO") from exc
        return {"mensaje": MSG_CREADO, "evento": _serializar(e)}

    def actualizar(self, ctx: AuthContext, pk: int, datos: dict[str, Any]) -> dict[str, Any]:
        try:
            e = Eventos_novedades.objects.select_related("id_sede").get(pk=pk)
        except Eventos_novedades.DoesNotExist as exc:
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="NO_ENCONTRADO") from exc
        version = int(datos.get("version_fila") or 0)
        if version != e.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        norm = self._validar_payload(datos, crear=False)
        norm["estado"] = bool(datos.get("estado", e.estado))
        antes = _serializar(e)
        try:
            with transaction.atomic():
                for k, v in norm.items():
                    setattr(e, k, v)
                e.version_fila = int(e.version_fila) + 1
                e.save()
                _auditar(ctx, "EDITAR", e.id_evento, antes, _serializar(e), self._audit)
        except Exception as exc:  # pragma: no cover
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="ERROR_INTERNO") from exc
        return {"mensaje": MSG_ACTUALIZADO, "evento": _serializar(e)}

    def guardar_imagen_evento(self, id_evento: int, nombre: str, contenido: bytes, mime: str) -> str:
        if mime not in MIME_OK or len(contenido) > MAX_IMAGEN or len(contenido) == 0:
            raise ReglaNegocioError(MSG_ARCHIVO, codigo="ARCHIVO_INVALIDO")
        if not Eventos_novedades.objects.filter(pk=id_evento).exists():
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="NO_ENCONTRADO")
        try:
            imagen = Image.open(io.BytesIO(contenido))
            imagen.verify()
            rgb = Image.open(io.BytesIO(contenido)).convert("RGB")
        except Exception:  # pragma: no cover
            raise ReglaNegocioError(MSG_ARCHIVO, codigo="ARCHIVO_INVALIDO") from None
        base = Path(settings.BASE_DIR) / "media" / "eventos"
        base.mkdir(parents=True, exist_ok=True)
        stem = f"{id_evento}-{uuid.uuid4().hex[:8]}"
        principal = base / f"{stem}.webp"
        rgb.save(principal, format="WEBP", quality=82)
        rel = f"eventos/{principal.name}"
        Eventos_novedades.objects.filter(pk=id_evento).update(imagen_url=rel)
        return rel
