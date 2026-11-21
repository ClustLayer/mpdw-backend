"""Slug dinámico (B-9: sin columna slug en BD)."""

from __future__ import annotations

import re
import unicodedata


def slugify_nombre(nombre: str) -> str:
    t = unicodedata.normalize("NFD", nombre or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")


def ruta_producto(id_producto: int, nombre: str) -> str:
    slug = slugify_nombre(nombre) or "producto"
    return f"{id_producto}-{slug}"


def parse_id_producto(slug_o_id: str) -> int | None:
    parte = (slug_o_id or "").strip().split("-", 1)[0]
    if parte.isdigit():
        return int(parte)
    return None
