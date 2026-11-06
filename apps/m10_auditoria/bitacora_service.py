# ==============================================================================
# Consulta de bitácora de auditoría (HU 82, solo lectura)
# ==============================================================================
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.m01_identidad.models import Usuarios
from apps.m10_auditoria.models import Auditoria
from contratos.excepciones import DominioError, ReglaNegocioError


@dataclass(frozen=True)
class PaginaBitacora:
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    mensaje: str


def _parse_int(param: str | None, default: int, *, min_v: int, max_v: int) -> int:
    try:
        v = int(param) if param is not None and str(param).strip() != "" else default
    except (TypeError, ValueError) as exc:
        raise DominioError("Paginación inválida.", codigo="PAGINACION_INVALIDA") from exc
    return min(max(v, min_v), max_v)


def _parse_dt(param: str | None, end_of_day: bool = False) -> datetime | None:
    if not param or not str(param).strip():
        return None
    raw = str(param).strip()
    try:
        if "T" in raw or raw.endswith("+00:00") or len(raw) > 10:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            d = date.fromisoformat(raw)
            t = time.max if end_of_day else time.min
            dt = datetime.combine(d, t)
    except ValueError as exc:
        raise DominioError("Rango de fechas inválido.", codigo="FECHAS_INVALIDAS") from exc
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _resumen_cambio(antes: dict[str, Any] | None, despues: dict[str, Any] | None) -> str:
    """Texto breve para la tabla (CA 2.2)."""
    if not antes and not despues:
        return "—"
    claves: set[str] = set()
    if isinstance(antes, dict):
        claves |= set(antes.keys())
    if isinstance(despues, dict):
        claves |= set(despues.keys())
    if not claves:
        return "Cambio registrado"
    muestra = sorted(claves)[:4]
    extra = len(claves) - len(muestra)
    suf = f" (+{extra} más)" if extra > 0 else ""
    return "Campos: " + ", ".join(muestra) + suf


class BitacoraAuditoriaService:
    """Listado filtrado y paginado de la tabla Auditoria (append-only)."""

    def listar(self, params: dict[str, str | None]) -> PaginaBitacora:
        page = _parse_int(params.get("page"), 1, min_v=1, max_v=10_000)
        page_size = _parse_int(params.get("page_size"), 20, min_v=1, max_v=100)

        id_usuario = params.get("id_usuario")
        accion = (params.get("accion") or "").strip()[:50]
        entidad = (params.get("entidad") or "").strip()[:100]
        id_entidad_raw = params.get("id_entidad")
        fecha_desde = _parse_dt(params.get("fecha_desde"), end_of_day=False)
        fecha_hasta = _parse_dt(params.get("fecha_hasta"), end_of_day=True)

        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise ReglaNegocioError(
                "La fecha inicial no puede ser posterior a la fecha final.",
                codigo="RANGO_FECHAS_INVALIDO",
            )

        qs: QuerySet[Auditoria] = Auditoria.objects.select_related("id_usuario").all()

        if id_usuario and str(id_usuario).strip():
            try:
                uid = int(id_usuario)
            except (TypeError, ValueError) as exc:
                raise DominioError("Filtro de usuario inválido.", codigo="FILTRO_INVALIDO") from exc
            qs = qs.filter(id_usuario_id=uid)

        if accion:
            qs = qs.filter(accion__icontains=accion)
        if entidad:
            qs = qs.filter(entidad__icontains=entidad)

        if id_entidad_raw and str(id_entidad_raw).strip():
            try:
                id_ent = int(id_entidad_raw)
            except (TypeError, ValueError) as exc:
                raise DominioError(
                    "Identificador de entidad inválido.", codigo="FILTRO_INVALIDO"
                ) from exc
            qs = qs.filter(id_entidad=id_ent)

        if fecha_desde:
            qs = qs.filter(fecha_hora__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_hora__lte=fecha_hasta)

        qs = qs.order_by("-fecha_hora", "-id_auditoria")
        total = qs.count()
        offset = (page - 1) * page_size
        filas = list(qs[offset : offset + page_size])

        items = [_fila(r) for r in filas]
        if total == 0:
            mensaje = "No hay registros de auditoría para los criterios indicados."
        else:
            mensaje = f"Mostrando {len(items)} de {total} registros."
        return PaginaBitacora(
            items=items, total=total, page=page, page_size=page_size, mensaje=mensaje
        )

    def opciones_usuarios(self, q: str, limit: int = 30) -> list[dict[str, Any]]:
        """Lista compacta para filtro con búsqueda (CA 2.1)."""
        limit = min(max(limit, 1), 100)
        texto = (q or "").strip()[:80]
        query = Usuarios.objects.filter(estado=True).select_related("id_rol")
        if texto:
            query = query.filter(
                Q(nombre__icontains=texto)
                | Q(apellido__icontains=texto)
                | Q(email__icontains=texto)
                | Q(documento__icontains=texto)
            )
        out: list[dict[str, Any]] = []
        for u in query.order_by("nombre", "apellido")[:limit]:
            nombre = f"{(u.nombre or '').strip()} {(u.apellido or '').strip()}".strip()
            out.append(
                {
                    "id_usuario": u.id_usuario,
                    "etiqueta": nombre or u.email,
                    "email": u.email,
                }
            )
        return out


def _fila(r: Auditoria) -> dict[str, Any]:
    u = r.id_usuario
    nombre = ""
    if u:
        nombre = f"{(u.nombre or '').strip()} {(u.apellido or '').strip()}".strip() or (u.email or "")
    ip_val = str(getattr(r, "ip", "") or "")[:45]
    return {
        "id_auditoria": r.id_auditoria,
        "fecha_hora": r.fecha_hora.isoformat() if r.fecha_hora else None,
        "usuario": {
            "id_usuario": u.id_usuario if u else None,
            "nombre": nombre,
            "email": u.email if u else None,
        },
        "accion": r.accion,
        "entidad": r.entidad,
        "id_entidad": r.id_entidad,
        "ip_origen": ip_val,
        "resumen": _resumen_cambio(r.datos_antes, r.datos_despues),
        "datos_anteriores": r.datos_antes,
        "datos_nuevos": r.datos_despues,
        "motivo": r.motivo,
        "resultado": r.resultado,
    }
