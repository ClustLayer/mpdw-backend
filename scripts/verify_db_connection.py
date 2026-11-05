"""Comprueba conectividad PostgreSQL usando DATABASE_URL del .env local (no versionado)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Instale dependencias con uv sync.", file=sys.stderr)
        return 1

    load_dotenv(ROOT / ".env", override=False)
    import os

    url = os.environ.get("DATABASE_URL") or os.environ.get("database_url")
    if not url:
        print("DATABASE_URL no esta definida en .env", file=sys.stderr)
        return 1

    try:
        import psycopg
    except ImportError:
        print("psycopg no disponible.", file=sys.stderr)
        return 1

    try:
        with psycopg.connect(url, connect_timeout=15) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001 — mensaje operativo para desarrollo
        print(f"No fue posible conectar: {exc}", file=sys.stderr)
        print(
            "Si el host db.<ref>.supabase.co solo tiene IPv6, use el pooler Session (IPv4) "
            "desde Supabase → Settings → Database → Connection string.",
            file=sys.stderr,
        )
        return 1

    print("Conexion PostgreSQL OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
