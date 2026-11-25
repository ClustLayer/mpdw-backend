"""Cliente MongoDB ligero con soporte de almacén falso en pruebas."""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

from django.conf import settings

from apps.m13_plataforma.observability.fake_mongo_store import FakeMongoStore

logger = logging.getLogger(__name__)


class MongoStore(Protocol):
    def insert_many(self, collection: str, docs: list[dict[str, Any]]) -> None: ...

    def insert_one(self, collection: str, doc: dict[str, Any]) -> None: ...


class PyMongoStore:
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import MongoClient

        self._db = MongoClient(uri, serverSelectionTimeoutMS=3000)[database]

    def insert_many(self, collection: str, docs: list[dict[str, Any]]) -> None:
        if docs:
            self._db[collection].insert_many(docs, ordered=False)

    def insert_one(self, collection: str, doc: dict[str, Any]) -> None:
        self._db[collection].insert_one(doc)


def build_store(uri_env: str, *, default_db: str = "mpdw_observability") -> MongoStore | None:
    if getattr(settings, "MPDW_OBSERVABILITY_FAKE_MONGO", False):
        return FakeMongoStore()
    uri = os.environ.get(uri_env, "").strip() or getattr(settings, uri_env, "") or ""
    if not uri:
        return None
    db_name = os.environ.get(f"{uri_env}_DB", default_db)
    try:
        return PyMongoStore(uri, db_name)
    except Exception:  # pragma: no cover
        logger.exception("No se pudo conectar a Mongo (%s).", uri_env)
        return None
