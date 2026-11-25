"""CRUD de promociones y sorteos (Épica 21)."""

from __future__ import annotations

import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from PIL import Image

from apps.m10_auditoria.services import AuditService
from apps.m21_promociones.mensajes import (
    MSG_ACTUALIZADO,
    MSG_ACTUALIZAR_ERROR,
    MSG_ARCHIVO,
    MSG_CONCURRENCIA,
    MSG_CREADO,
    MSG_CREAR_ERROR,
    MSG_FECHAS,
    MSG_LISTADO,
    MSG_OBLIGATORIOS,
    MSG_PUBLICOS,
    MSG_SIN_COINCIDENCIAS,
    MSG_TIPO,
)
from apps.m21_promociones.models import ESTADO_ACTIVA, TIPO_PROMOCION, TIPO_SORTEO, Promociones
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ReglaNegocioError

BOGOTA = ZoneInfo("America/Bogota")
TIPOS_VALIDOS = {TIPO_PROMOCION, TIPO_SORTEO}
MAX_IMAGEN = 2 * 1024 * 1024
MIME_OK = {"image/jpeg": "jpg", "image/png": "png"}
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


def _serializar(p: Promociones) -> dict[str, Any]:
    return {
        "id_promocion": p.id_promocion,
        "titulo": p.titulo,
        "tipo": p.tipo,
        "descripcion": p.descripcion,
        "hashtags": p.hashtags,
        "imagen": p.imagen,
        "fecha_inicio": p.fecha_inicio.isoformat() if p.fecha_inicio else None,
        "fecha_fin": p.fecha_fin.isoformat() if p.fecha_fin else None,
        "estado": p.estado,
        "version_fila": p.version_fila,
        "fecha_registro": p.fecha_registro.isoformat() if p.fecha_registro else None,
    }


def _auditar(ctx: AuthContext, accion: str, entidad_id: int, audit: AuditService) -> None:
    audit.registrar(
        AuditoriaDTO(
            id_usuario=ctx.id_usuario,
            accion=accion,
            entidad="Promociones",
            id_entidad=entidad_id,
            motivo=accion,
            id_correlacion=ctx.id_correlacion,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    )


def _vigente_ahora(p: Promociones, ahora: datetime) -> bool:
    if p.estado != ESTADO_ACTIVA or not (p.imagen or "").strip():
        return False
    inicio = p.fecha_inicio
    fin = p.fecha_fin
    if inicio and ahora < inicio:
        return False
    if fin and ahora > fin:
        return False
    return True


class AdminPromocionesService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()

    def listar(self, q: str, estado: str | None, page: int, page_size: int) -> dict[str, Any]:
        qs = Promociones.objects.all()
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(titulo__icontains=texto)
                | Q(descripcion__icontains=texto)
                | Q(hashtags__icontains=texto)
            )
        est = (estado or "todos").lower()
        if est in {"activa", "pausada"}:
            qs = qs.filter(estado=est)
        total = qs.count()
        if total == 0 and texto:
            return {
                "items": [],
                "total": 0,
                "mensaje": MSG_SIN_COINCIDENCIAS,
                "page": page,
                "page_size": page_size,
            }
        offset = max(0, (max(1, page) - 1) * page_size)
        filas = [_serializar(p) for p in qs.order_by("-fecha_inicio")[offset : offset + page_size]]
        return {
            "items": filas,
            "total": total,
            "mensaje": MSG_LISTADO.format(n=len(filas), total=total),
            "page": page,
            "page_size": page_size,
        }

    def obtener(self, pk: int) -> dict[str, Any]:
        p = Promociones.objects.get(pk=pk)
        return _serializar(p)

    def publicas(self) -> dict[str, Any]:
        ahora = timezone.now().astimezone(BOGOTA)
        qs = Promociones.objects.filter(estado=ESTADO_ACTIVA).exclude(imagen="").order_by("-fecha_inicio")
        items = []
        for p in qs[:100]:
            if not _vigente_ahora(p, ahora):
                continue
            data = _serializar(p)
            data["imagen"] = _imagen_publica(data.get("imagen") or "")
            items.append(data)
            if len(items) >= 50:
                break
        return {"items": items, "mensaje": MSG_PUBLICOS}

    def _validar(self, datos: dict[str, Any], *, crear: bool) -> dict[str, Any]:
        titulo = (datos.get("titulo") or "").strip()
        descripcion = (datos.get("descripcion") or "").strip()
        tipo = (datos.get("tipo") or "").strip().lower()
        if not titulo or not descripcion or not tipo:
            raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        if tipo not in TIPOS_VALIDOS:
            raise ReglaNegocioError(MSG_TIPO, codigo="TIPO_INVALIDO")
        inicio = _parse_dt(datos.get("fecha_inicio"))
        if not inicio:
            raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        fin = _parse_dt(datos.get("fecha_fin"))
        if fin and fin < inicio:
            raise ReglaNegocioError(MSG_FECHAS, codigo="FECHAS_INVALIDAS")
        estado = (datos.get("estado") or ESTADO_ACTIVA).strip().lower()
        if estado not in {"activa", "pausada"}:
            estado = ESTADO_ACTIVA
        return {
            "titulo": titulo[:150],
            "tipo": tipo,
            "descripcion": descripcion,
            "hashtags": (datos.get("hashtags") or "").strip()[:500],
            "imagen": (datos.get("imagen") or "").strip()[:500],
            "fecha_inicio": inicio,
            "fecha_fin": fin,
            "estado": estado,
        }

    def crear(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        norm = self._validar(datos, crear=True)
        try:
            with transaction.atomic():
                p = Promociones.objects.create(**norm)
                _auditar(ctx, "CREAR_PROMOCION", p.id_promocion, self._audit)
        except Exception as exc:  # pragma: no cover
            raise ReglaNegocioError(MSG_CREAR_ERROR, codigo="ERROR_INTERNO") from exc
        return {"mensaje": MSG_CREADO, "promocion": _serializar(p)}

    def actualizar(self, ctx: AuthContext, pk: int, datos: dict[str, Any]) -> dict[str, Any]:
        try:
            p = Promociones.objects.get(pk=pk)
        except Promociones.DoesNotExist as exc:
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="NO_ENCONTRADO") from exc
        version = int(datos.get("version_fila") or 0)
        if version != p.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        norm = self._validar(datos, crear=False)
        try:
            with transaction.atomic():
                for k, v in norm.items():
                    setattr(p, k, v)
                p.version_fila = int(p.version_fila) + 1
                p.save()
                _auditar(ctx, "EDITAR_PROMOCION", p.id_promocion, self._audit)
        except Exception as exc:  # pragma: no cover
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="ERROR_INTERNO") from exc
        return {"mensaje": MSG_ACTUALIZADO, "promocion": _serializar(p)}

    def guardar_imagen(self, id_promocion: int, nombre: str, contenido: bytes, mime: str) -> str:
        if mime not in MIME_OK or len(contenido) > MAX_IMAGEN or len(contenido) == 0:
            raise ReglaNegocioError(MSG_ARCHIVO, codigo="ARCHIVO_INVALIDO")
        if not Promociones.objects.filter(pk=id_promocion).exists():
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="NO_ENCONTRADO")
        try:
            imagen = Image.open(io.BytesIO(contenido))
            imagen.verify()
            rgb = Image.open(io.BytesIO(contenido))
            if mime == "image/png":
                rgb = rgb.convert("RGBA")
            else:
                rgb = rgb.convert("RGB")
        except Exception:  # pragma: no cover
            raise ReglaNegocioError(MSG_ARCHIVO, codigo="ARCHIVO_INVALIDO") from None
        ext = MIME_OK[mime]
        base = Path(settings.BASE_DIR) / "media" / "promociones"
        base.mkdir(parents=True, exist_ok=True)
        stem = f"{id_promocion}-{uuid.uuid4().hex[:8]}"
        principal = base / f"{stem}.{ext}"
        if ext == "png":
            rgb.save(principal, format="PNG", optimize=True)
        else:
            rgb.save(principal, format="JPEG", quality=85)
        rel = f"promociones/{principal.name}"
        Promociones.objects.filter(pk=id_promocion).update(imagen=rel)
        return rel
