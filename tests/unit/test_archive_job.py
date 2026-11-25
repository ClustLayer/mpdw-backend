"""Pruebas del archivo bimestral de logs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from apps.m13_plataforma.observability.archive_job import (
    ejecutar_archivo,
    periodo_cerrado_anterior,
)


def test_periodo_cerrado_marzo_archiva_ene_feb():
    p = periodo_cerrado_anterior(datetime(2026, 3, 3, tzinfo=UTC))
    assert p.etiqueta == "2026/01-02"
    assert p.inicio == datetime(2026, 1, 1, tzinfo=UTC)
    assert p.fin == datetime(2026, 3, 1, tzinfo=UTC)


def test_periodo_cerrado_enero_archiva_nov_dic():
    p = periodo_cerrado_anterior(datetime(2026, 1, 4, tzinfo=UTC))
    assert p.etiqueta == "2025/11-12"
    assert p.fin == datetime(2026, 1, 1, tzinfo=UTC)


def test_ejecutar_archivo_idempotente(tmp_path: Path, monkeypatch):
    contingencia = tmp_path / "auditoria_migracion_backup.jsonl"
    contingencia.write_text(
        json.dumps({"tipo": "auditoria_migrada", "accion": "CREAR_EVENTO"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "media" / "backups").mkdir(parents=True)
    contingencia.rename(tmp_path / "media" / "backups" / "auditoria_migracion_backup.jsonl")

    monkeypatch.setattr(
        "apps.m13_plataforma.observability.archive_job._fetch_docs",
        lambda *a, **k: [],
    )
    destino = tmp_path / "out"
    m1 = ejecutar_archivo(destino_raiz=destino, periodo=periodo_cerrado_anterior(datetime(2026, 3, 2, tzinfo=UTC)))
    assert m1["estado"] == "VALIDADO"
    assert m1["total_registros"] >= 1
    m2 = ejecutar_archivo(destino_raiz=destino, periodo=periodo_cerrado_anterior(datetime(2026, 3, 2, tzinfo=UTC)))
    assert any(a.get("reutilizado") for a in m2["archivos"])
