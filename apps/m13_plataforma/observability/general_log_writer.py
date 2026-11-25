"""Escritura asíncrona de logs generales con cola de reintentos."""

from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import UTC
from typing import Any

from django.utils import timezone

from apps.m10_auditoria.sanitize import sanitize_auditoria_payload
from apps.m13_plataforma.observability.constants import COLECCION_LOGS_GENERALES
from apps.m13_plataforma.observability.mongo_client import MongoStore, build_store

logger = logging.getLogger(__name__)

_writer: GeneralLogWriter | None = None
_writer_lock = threading.Lock()


class GeneralLogWriter:
    def __init__(self, store: MongoStore | None) -> None:
        self._store = store
        self._pending: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._retry: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run, name="general-log-writer", daemon=True)
        self._worker.start()

    def enqueue(self, doc: dict[str, Any]) -> None:
        """Encola sin bloquear la petición HTTP."""
        payload = dict(doc)
        payload.setdefault("fecha_hora", timezone.now().astimezone(UTC).isoformat())
        if "datos_antes" in payload:
            payload["datos_antes"] = sanitize_auditoria_payload(payload.get("datos_antes"))
        if "datos_despues" in payload:
            payload["datos_despues"] = sanitize_auditoria_payload(payload.get("datos_despues"))
        try:
            self._pending.put_nowait(payload)
        except queue.Full:  # pragma: no cover
            logger.warning(
                "Cola de logs generales llena; descartando evento %s", payload.get("accion")
            )

    def log_http(
        self, *, metodo: str, ruta: str, status: int, correlation_id: str, ms: float
    ) -> None:
        self.enqueue(
            {
                "tipo": "http_request",
                "metodo": metodo,
                "ruta": ruta,
                "status": status,
                "id_correlacion": correlation_id,
                "duracion_ms": round(ms, 2),
            }
        )

    def shutdown(self) -> None:
        self._stop.set()
        self._pending.put(None)
        self._worker.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._pending.get(timeout=0.25)
            except queue.Empty:
                self._flush_retries()
                continue
            if item is None:
                break
            if not self._store:
                continue
            if not self._persist(item):
                self._retry.append(item)
            self._flush_retries()

    def _flush_retries(self) -> None:
        if not self._store or not self._retry:
            return
        batch, self._retry = self._retry[:20], self._retry[20:]
        for doc in batch:
            if not self._persist(doc):
                self._retry.append(doc)
                break
        if self._retry:
            time.sleep(0.05)

    def _persist(self, doc: dict[str, Any]) -> bool:
        if not self._store:
            return True
        try:
            self._store.insert_one(COLECCION_LOGS_GENERALES, doc)
            return True
        except Exception:  # pragma: no cover
            logger.exception("Fallo al escribir log general en Mongo.")
            return False


def get_general_log_writer() -> GeneralLogWriter:
    global _writer
    with _writer_lock:
        if _writer is None:
            store = build_store("MONGODB_GENERAL_URI")
            _writer = GeneralLogWriter(store)
        return _writer
