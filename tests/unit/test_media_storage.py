"""Cobertura del helper de almacenamiento de imágenes."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.m13_plataforma.media_storage import (
    guardar_bytes_publicos,
    storage_configurado,
    url_publica_o_media,
)
from contratos.excepciones import ReglaNegocioError

pytestmark = pytest.mark.unit


def test_url_publica_o_media():
    assert url_publica_o_media("") == ""
    assert url_publica_o_media("https://cdn/x.webp") == "https://cdn/x.webp"
    assert url_publica_o_media("/api/v1/catalogo/media/x.webp") == "/api/v1/catalogo/media/x.webp"
    assert url_publica_o_media("productos/a.webp") == "/api/v1/catalogo/media/productos/a.webp"


@pytest.mark.django_db
def test_guardar_bytes_local_en_testing(settings, tmp_path, monkeypatch):
    settings.TESTING = True
    settings.BASE_DIR = tmp_path
    settings.SUPABASE_STORAGE_URL = ""
    settings.SUPABASE_STORAGE_SERVICE_KEY = ""
    settings.SUPABASE_URL = ""
    settings.SUPABASE_SERVICE_ROLE_KEY = ""
    assert storage_configurado() is False
    ruta = guardar_bytes_publicos("productos/demo.webp", b"abc", "image/webp")
    assert ruta == "productos/demo.webp"
    assert (Path(tmp_path) / "media" / "productos" / "demo.webp").read_bytes() == b"abc"


@pytest.mark.django_db
def test_guardar_bytes_supabase(monkeypatch, settings):
    settings.SUPABASE_STORAGE_URL = "https://example.supabase.co/storage/v1"
    settings.SUPABASE_STORAGE_SERVICE_KEY = "key"
    settings.SUPABASE_PUBLIC_BUCKET = "medios-publicos"

    class Fake:
        def subir_archivo_publico(self, contenido, ruta, mime):
            assert contenido == b"img"
            assert ruta == "eventos/x.webp"
            return "https://example.supabase.co/storage/v1/object/public/medios-publicos/eventos/x.webp"

    monkeypatch.setattr(
        "apps.m13_plataforma.media_storage.SupabaseStorageAdapter",
        lambda: Fake(),
    )
    url = guardar_bytes_publicos("eventos/x.webp", b"img", "image/webp")
    assert url.startswith("https://")


@pytest.mark.django_db
def test_guardar_bytes_falla_sin_config_en_prod(settings):
    settings.TESTING = False
    settings.DEBUG = False
    settings.SUPABASE_STORAGE_URL = ""
    settings.SUPABASE_STORAGE_SERVICE_KEY = ""
    settings.SUPABASE_URL = ""
    settings.SUPABASE_SERVICE_ROLE_KEY = ""
    with pytest.raises(ReglaNegocioError):
        guardar_bytes_publicos("x.webp", b"1", "image/webp")


@pytest.mark.django_db
def test_guardar_bytes_supabase_error(monkeypatch, settings):
    settings.SUPABASE_STORAGE_URL = "https://example.supabase.co/storage/v1"
    settings.SUPABASE_STORAGE_SERVICE_KEY = "key"

    class Boom:
        def subir_archivo_publico(self, *a, **k):
            raise RuntimeError("fail")

    monkeypatch.setattr(
        "apps.m13_plataforma.media_storage.SupabaseStorageAdapter",
        lambda: Boom(),
    )
    with pytest.raises(ReglaNegocioError) as exc:
        guardar_bytes_publicos("eventos/y.webp", b"img", "image/webp")
    assert exc.value.codigo == "STORAGE_ERROR"
