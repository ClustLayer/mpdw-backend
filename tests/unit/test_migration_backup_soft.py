"""Respaldo de migración con fallback JSONL."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.m13_plataforma.observability import migration_backup as mb

pytestmark = pytest.mark.unit


def _row(accion: str = "EDITAR_EVENTO") -> SimpleNamespace:
    return SimpleNamespace(
        id_auditoria=3,
        id_usuario_id=1,
        id_usuario=None,
        accion=accion,
        entidad="Eventos",
        id_entidad=1,
        motivo="m",
        resultado="EXITO",
        ip="127.0.0.1",
        user_agent="",
        id_correlacion="",
        fecha_hora=None,
    )


def test_row_to_doc_basico():
    doc = mb.row_to_doc(_row())
    assert doc["accion"] == "EDITAR_EVENTO"
    assert doc["tipo"] == "auditoria_migrada"


def test_backup_rows_sin_uri(monkeypatch):
    monkeypatch.delenv("MONGODB_GENERAL_URI", raising=False)
    assert mb.backup_rows([_row()]) == 1
    assert mb.backup_rows([]) == 0


def test_backup_rows_uri_falla_escribe_jsonl(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MONGODB_GENERAL_URI", "mongodb://invalid")
    monkeypatch.delenv("MONGODB_BACKUP_STRICT", raising=False)

    class Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("atlas down")

    monkeypatch.setattr(mb, "FakeMongoStore", mb.FakeMongoStore)

    import apps.m13_plataforma.observability.mongo_client as mc

    monkeypatch.setattr(mc, "PyMongoStore", Boom)
    n = mb.backup_rows([_row()])
    assert n == 1
    out = Path("media/backups/auditoria_migracion_backup.jsonl")
    assert out.exists()
    assert "EDITAR_EVENTO" in out.read_text(encoding="utf-8")
