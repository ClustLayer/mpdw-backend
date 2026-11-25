"""Registro por lotes de clics / interacciones para analítica."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from django.utils import timezone

from apps.m13_plataforma.observability.constants import COLECCION_INTERACCIONES
from apps.m13_plataforma.observability.mongo_client import MongoStore, build_store

_store: MongoStore | None | bool = False


def _store_interactions() -> MongoStore | None:
    global _store
    if _store is False:
        _store = build_store("MONGODB_INTERACTIONS_URI") or build_store("MONGODB_GENERAL_URI")
    return _store if _store is not False else None


def _normalizar_evento(ev: dict[str, Any]) -> dict[str, Any]:
    boton = str(ev.get("boton") or ev.get("elemento") or ev.get("target") or "")[:200]
    pantalla = str(ev.get("pantalla") or ev.get("ruta") or ev.get("path") or "")[:500]
    meta = ev.get("metadata") if isinstance(ev.get("metadata"), dict) else {}
    promo = ev.get("id_promocion")
    if promo is not None and "id_promocion" not in meta:
        try:
            meta = {**meta, "id_promocion": int(promo)}
        except (TypeError, ValueError):
            pass
    return {
        "evento": str(ev.get("evento") or ev.get("tipo") or boton or "click")[:80],
        "ruta": pantalla,
        "elemento": boton,
        "pantalla": pantalla,
        "boton": boton,
        "metadata": meta,
        "id_promocion": meta.get("id_promocion"),
        "sede": ev.get("sede") or ev.get("id_sede"),
    }


def registrar_lote(
    *,
    id_usuario: int | None,
    eventos: list[dict[str, Any]],
    id_correlacion: str = "",
) -> dict[str, Any]:
    if not eventos:
        return {"registrados": 0, "mensaje": "Sin eventos."}
    ahora = timezone.now().astimezone(UTC).isoformat()
    docs: list[dict[str, Any]] = []
    for raw in eventos[:200]:
        if not isinstance(raw, dict):
            continue
        norm = _normalizar_evento(raw)
        docs.append(
            {
                "id_usuario": id_usuario,
                "evento": norm["evento"],
                "ruta": norm["ruta"],
                "elemento": norm["elemento"],
                "boton": norm["boton"],
                "pantalla": norm["pantalla"],
                "id_promocion": norm.get("id_promocion"),
                "sede": norm.get("sede"),
                "metadata": norm["metadata"],
                "id_correlacion": id_correlacion,
                "fecha_hora": ahora,
            }
        )
    if not docs:
        return {"registrados": 0, "mensaje": "Sin eventos."}
    store = _store_interactions()
    if store:
        try:
            store.insert_many(COLECCION_INTERACCIONES, docs)
        except Exception:
            # Nunca bloquear la UI por telemetría
            return {"registrados": 0, "mensaje": "Telemetría diferida."}
    return {"registrados": len(docs), "mensaje": f"Se registraron {len(docs)} interacciones."}