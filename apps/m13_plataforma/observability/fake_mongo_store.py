"""Almacén en memoria para pruebas unitarias sin MongoDB."""

from __future__ import annotations

from threading import Lock
from typing import Any


class FakeMongoStore:
    """Implementación mínima compatible con la interfaz usada por GeneralLogWriter."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.documents: dict[str, list[dict[str, Any]]] = {}

    def insert_many(self, collection: str, docs: list[dict[str, Any]]) -> None:
        if not docs:
            return
        with self._lock:
            self.documents.setdefault(collection, []).extend(docs)

    def insert_one(self, collection: str, doc: dict[str, Any]) -> None:
        self.insert_many(collection, [doc])
