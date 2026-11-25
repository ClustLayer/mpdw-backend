"""Subida de imágenes públicas a Supabase Storage (sin depender del filesystem del servidor)."""

from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings

from apps.m13_plataforma.adapters.storage_supabase import SupabaseStorageAdapter
from contratos.excepciones import ReglaNegocioError

logger = logging.getLogger(__name__)


def storage_configurado() -> bool:
    url = (
        getattr(settings, "SUPABASE_STORAGE_URL", "") or getattr(settings, "SUPABASE_URL", "") or ""
    ).strip()
    key = (
        getattr(settings, "SUPABASE_STORAGE_SERVICE_KEY", "")
        or getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
        or ""
    ).strip()
    return bool(url and key)


def guardar_bytes_publicos(ruta_relativa: str, contenido: bytes, mime: str) -> str:
    """
    Persiste en el bucket público de Supabase y retorna la URL pública absoluta.
    En TESTING sin credenciales, escribe en media/ local y retorna la ruta relativa.
    """
    ruta = ruta_relativa.lstrip("/")
    if storage_configurado():
        try:
            return SupabaseStorageAdapter().subir_archivo_publico(contenido, ruta, mime)
        except Exception as exc:
            logger.exception("Fallo subida Supabase Storage (%s)", ruta)
            raise ReglaNegocioError(
                "No fue posible almacenar la imagen en el almacenamiento remoto.",
                codigo="STORAGE_ERROR",
            ) from exc

    if getattr(settings, "TESTING", False) or getattr(settings, "DEBUG", False):
        base = Path(settings.BASE_DIR) / "media"
        destino = base / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
        logger.warning("Storage remoto no configurado; imagen en media local: %s", ruta)
        return ruta

    raise ReglaNegocioError(
        "Almacenamiento remoto no configurado (SUPABASE_STORAGE_URL / SUPABASE_STORAGE_SERVICE_KEY).",
        codigo="STORAGE_NO_CONFIGURADO",
    )


def url_publica_o_media(valor: str) -> str:
    """Normaliza rutas relativas a URL de media API; deja absolutas intactas."""
    url = (valor or "").strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://", "/")):
        return url
    return f"/api/v1/catalogo/media/{url.lstrip('/')}"
