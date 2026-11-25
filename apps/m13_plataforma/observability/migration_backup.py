"""Respaldo de filas de auditoría no seguridad hacia Mongo durante migraciones."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from apps.m13_plataforma.observability.constants import (
    ACCIONES_SEGURIDAD_SQL,
    COLECCION_LOGS_GENERALES,
)
from apps.m13_plataforma.observability.fake_mongo_store import FakeMongoStore

logger = logging.getLogger(__name__)


def _accion_sql(accion: str) -> bool:
    return str(accion or "").upper() in ACCIONES_SEGURIDAD_SQL


def row_to_doc(row: Any) -> dict[str, Any]:
    usuario = getattr(row, "id_usuario_id", None)
    if usuario is None and getattr(row, "id_usuario", None) is not None:
        usuario = row.id_usuario_id
    fh = getattr(row, "fecha_hora", None)
    return {
        "tipo": "auditoria_migrada",
        "id_auditoria_origen": getattr(row, "id_auditoria", None),
        "id_usuario": usuario,
        "accion": getattr(row, "accion", ""),
        "entidad": getattr(row, "entidad", ""),
        "id_entidad": getattr(row, "id_entidad", None),
        "motivo": getattr(row, "motivo", ""),
        "resultado": getattr(row, "resultado", "EXITO"),
        "ip": getattr(row, "ip", ""),
        "user_agent": getattr(row, "user_agent", ""),
        "id_correlacion": getattr(row, "id_correlacion", ""),
        "fecha_hora": fh.isoformat() if fh else datetime.now(UTC).isoformat(),
        "migrado_en": datetime.now(UTC).isoformat(),
    }


def backup_rows(rows: list[Any]) -> int:
    """Copia documentos a Mongo (o FakeMongoStore si no hay URI). Retorna cantidad respaldada."""
    docs = [row_to_doc(r) for r in rows if not _accion_sql(getattr(r, "accion", ""))]
    if not docs:
        return 0
    uri = os.environ.get("MONGODB_GENERAL_URI", "").strip()
    if not uri:
        store: Any = FakeMongoStore()
        store.insert_many(COLECCION_LOGS_GENERALES, docs)
        logger.warning(
            "MONGODB_GENERAL_URI ausente: respaldo de %s filas en FakeMongoStore (solo trazas).", len(docs)
        )
        return len(docs)
    try:
        from apps.m13_plataforma.observability.mongo_client import PyMongoStore

        db = os.environ.get("MONGODB_GENERAL_URI_DB", "mpdw_observability")
        PyMongoStore(uri, db).insert_many(COLECCION_LOGS_GENERALES, docs)
        return len(docs)
    except Exception:
        logger.exception("Fallo respaldo Mongo; abortando migración de limpieza.")
        raise
