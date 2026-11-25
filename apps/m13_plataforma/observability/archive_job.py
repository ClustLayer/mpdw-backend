"""Archivo bimestral de logs: exportar → verificar → (opcional) retener/eliminar."""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from apps.m13_plataforma.observability.constants import (
    COLECCION_INTERACCIONES,
    COLECCION_LOGS_GENERALES,
)
from apps.m13_plataforma.observability.mongo_client import build_store

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PeriodoBimestral:
    anio: int
    mes_inicio: int  # 1, 3, 5, 7, 9, 11
    etiqueta: str  # "2026/01-02"
    inicio: datetime
    fin: datetime  # exclusivo


def periodo_cerrado_anterior(ahora: datetime | None = None) -> PeriodoBimestral:
    """Periodo bimestral calendario ya cerrado (UTC)."""
    now = ahora or datetime.now(UTC)
    mes = now.month
    anio = now.year
    # El periodo cerrado termina al inicio del bimestral actual.
    if mes % 2 == 0:
        mes_inicio_actual = mes - 1
    else:
        mes_inicio_actual = mes
    # Retroceder un bimestre
    if mes_inicio_actual == 1:
        anio_p = anio - 1
        mes_inicio = 11
    else:
        anio_p = anio
        mes_inicio = mes_inicio_actual - 2
    mes_fin = mes_inicio + 1
    inicio = datetime(anio_p, mes_inicio, 1, tzinfo=UTC)
    if mes_inicio == 11:
        fin = datetime(anio_p + 1, 1, 1, tzinfo=UTC)
    else:
        fin = datetime(anio_p, mes_inicio + 2, 1, tzinfo=UTC)
    etiqueta = f"{anio_p}/{mes_inicio:02d}-{mes_fin:02d}"
    return PeriodoBimestral(anio_p, mes_inicio, etiqueta, inicio, fin)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch_docs(uri_env: str, collection: str, inicio: datetime, fin: datetime) -> list[dict[str, Any]]:
    store = build_store(uri_env)
    if store is None:
        logger.warning("Sin almacén para %s; colección %s omitida.", uri_env, collection)
        return []
    # PyMongoStore no expone find; acceso directo al cliente si es real.
    db = getattr(store, "_db", None)
    if db is None:
        return []
    cursor = db[collection].find(
        {
            "$or": [
                {"fecha_hora": {"$gte": inicio.isoformat(), "$lt": fin.isoformat()}},
                {"timestamp": {"$gte": inicio.isoformat(), "$lt": fin.isoformat()}},
                {"creado_en": {"$gte": inicio.isoformat(), "$lt": fin.isoformat()}},
            ]
        }
    )
    docs: list[dict[str, Any]] = []
    for doc in cursor:
        doc.pop("_id", None)
        docs.append(doc)
    return docs


def _escribir_jsonl_gz(path: Path, docs: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(json.dumps(doc, ensure_ascii=False, default=str) + "\n")
            n += 1
    return n


def _validar_jsonl_gz(path: Path) -> int:
    n = 0
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            json.loads(line)
            n += 1
    return n


def ejecutar_archivo(
    *,
    destino_raiz: Path | None = None,
    periodo: PeriodoBimestral | None = None,
    incluir_contingencia_local: bool = True,
) -> dict[str, Any]:
    """
    Exporta logs del periodo a JSONL.gz + manifiesto con checksum.
    No elimina datos operativos; la limpieza es un paso separado y condicionado.
    """
    p = periodo or periodo_cerrado_anterior()
    raiz = destino_raiz or (Path("media") / "backups" / "logs" / p.etiqueta.replace("/", "-"))
    raiz.mkdir(parents=True, exist_ok=True)

    fuentes: list[tuple[str, str, list[dict[str, Any]]]] = [
        ("general_logs", "MONGODB_GENERAL_URI", _fetch_docs("MONGODB_GENERAL_URI", COLECCION_LOGS_GENERALES, p.inicio, p.fin)),
        (
            "interacciones",
            "MONGODB_INTERACTIONS_URI",
            _fetch_docs("MONGODB_INTERACTIONS_URI", COLECCION_INTERACCIONES, p.inicio, p.fin),
        ),
    ]

    if incluir_contingencia_local:
        contingencia = Path("media") / "backups" / "auditoria_migracion_backup.jsonl"
        if contingencia.exists():
            docs_local: list[dict[str, Any]] = []
            with contingencia.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        docs_local.append(json.loads(line))
            fuentes.append(("auditoria_migracion_contingencia", "local", docs_local))

    archivos_meta: list[dict[str, Any]] = []
    total = 0
    for nombre, origen, docs in fuentes:
        out = raiz / f"{nombre}.jsonl.gz"
        if out.exists() and out.stat().st_size > 0:
            # Idempotente: no reescribir si ya hay archivo válido
            try:
                leidos = _validar_jsonl_gz(out)
                archivos_meta.append(
                    {
                        "archivo": out.name,
                        "origen": origen,
                        "registros": leidos,
                        "bytes": out.stat().st_size,
                        "sha256": _sha256_file(out),
                        "reutilizado": True,
                    }
                )
                total += leidos
                continue
            except Exception:
                logger.warning("Archivo existente inválido; se regenera: %s", out)

        n = _escribir_jsonl_gz(out, docs)
        leidos = _validar_jsonl_gz(out)
        if leidos != n:
            raise RuntimeError(f"Inconsistencia al validar {out}: escritos={n} leidos={leidos}")
        archivos_meta.append(
            {
                "archivo": out.name,
                "origen": origen,
                "registros": n,
                "bytes": out.stat().st_size,
                "sha256": _sha256_file(out),
                "reutilizado": False,
            }
        )
        total += n

    manifiesto = {
        "periodo": p.etiqueta,
        "inicio_utc": p.inicio.isoformat(),
        "fin_utc_exclusivo": p.fin.isoformat(),
        "creado_en": datetime.now(UTC).isoformat(),
        "total_registros": total,
        "archivos": archivos_meta,
        "estado": "VALIDADO",
        "nota": "Backup ≠ borrado. Aplicar retención solo tras verificar checksum y lectura.",
    }
    man_path = raiz / "manifest.json"
    man_path.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Archivo bimestral listo en %s (%s registros).", raiz, total)
    return manifiesto
