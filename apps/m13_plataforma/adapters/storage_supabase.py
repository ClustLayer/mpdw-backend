# ==============================================================================
# Adaptador Real Supabase Storage (HTTPX) - MPDW
# SAD Ref: ADR-011, I-04, §10.7
# ==============================================================================
import logging

import httpx
from django.conf import settings

from contratos.puertos.almacenamiento import FileStoragePort

logger = logging.getLogger(__name__)


def _storage_root(supabase_url: str | None = None) -> str:
    """Normaliza a .../storage/v1 sin barra final."""
    raw = (
        supabase_url
        or getattr(settings, "SUPABASE_STORAGE_URL", "")
        or getattr(settings, "SUPABASE_URL", "")
        or "http://localhost:54321"
    )
    base = str(raw).rstrip("/")
    if base.endswith("/storage/v1"):
        return base
    return f"{base}/storage/v1"


def _service_key(service_key: str | None = None) -> str:
    return str(
        service_key
        or getattr(settings, "SUPABASE_STORAGE_SERVICE_KEY", "")
        or getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
        or ""
    )


def _bucket_publico(default: str = "medios-publicos") -> str:
    return str(getattr(settings, "SUPABASE_PUBLIC_BUCKET", "") or default)


def _bucket_privado(default: str = "adjuntos-privados") -> str:
    return str(getattr(settings, "SUPABASE_PRIVATE_BUCKET", "") or default)


class SupabaseStorageAdapter(FileStoragePort):
    """Adaptador de Supabase Storage para buckets publicos y privados."""

    def __init__(
        self,
        supabase_url: str | None = None,
        service_key: str | None = None,
        bucket_publico: str | None = None,
        bucket_privado: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._storage_root = _storage_root(supabase_url)
        # Origen del proyecto sin /storage/v1 (para URLs públicas).
        self._project_origin = (
            self._storage_root[: -len("/storage/v1")]
            if self._storage_root.endswith("/storage/v1")
            else self._storage_root
        )
        self._key = _service_key(service_key)
        self._bucket_publico = bucket_publico or _bucket_publico()
        self._bucket_privado = bucket_privado or _bucket_privado()
        self._client = client or httpx.Client(timeout=15.0)

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        return {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }

    def subir_archivo_publico(self, contenido: bytes, ruta_destino: str, tipo_mime: str) -> str:
        """Sube un archivo al bucket publico y retorna la URL publica."""
        ruta = ruta_destino.lstrip("/")
        url = f"{self._storage_root}/object/{self._bucket_publico}/{ruta}"
        headers = self._headers(content_type=tipo_mime)

        try:
            resp = self._client.post(url, content=contenido, headers=headers, timeout=15.0)
            if resp.status_code in (200, 201):
                return (
                    f"{self._project_origin}/storage/v1/object/public/{self._bucket_publico}/{ruta}"
                )
            logger.error("Error al subir a Supabase Storage: %s - %s", resp.status_code, resp.text)
            raise RuntimeError(f"Error en Supabase Storage: {resp.status_code}")
        except httpx.HTTPError as err:
            logger.error("Fallo de red en Supabase Storage: %s", err)
            raise RuntimeError(f"Error de conexion con Supabase Storage: {err}") from err

    def subir_archivo_privado(self, contenido: bytes, ruta_destino: str, tipo_mime: str) -> str:
        """Sube un archivo al bucket privado y retorna la ruta interna."""
        ruta = ruta_destino.lstrip("/")
        url = f"{self._storage_root}/object/{self._bucket_privado}/{ruta}"
        headers = self._headers(content_type=tipo_mime)

        try:
            resp = self._client.post(url, content=contenido, headers=headers, timeout=15.0)
            if resp.status_code in (200, 201):
                return ruta
            logger.error("Error al subir archivo privado: %s - %s", resp.status_code, resp.text)
            raise RuntimeError(f"Error en Supabase Storage Privado: {resp.status_code}")
        except httpx.HTTPError as err:
            logger.error("Fallo de red en Supabase Storage Privado: %s", err)
            raise RuntimeError(f"Error de conexion con Supabase Storage: {err}") from err

    def obtener_url_firmada(self, ruta_privada: str, segundos_validez: int = 3600) -> str:
        """Genera una URL firmada de descarga temporal para un objeto privado."""
        url = f"{self._storage_root}/object/sign/{self._bucket_privado}/{ruta_privada.lstrip('/')}"
        payload = {"expiresIn": segundos_validez}
        headers = self._headers()

        try:
            resp = self._client.post(url, json=payload, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                signed_path = data.get("signedURL", "")
                return f"{self._storage_root}{signed_path}"
            return ""
        except httpx.HTTPError:
            return ""

    def eliminar_archivo(self, bucket: str, ruta: str) -> bool:
        """Elimina un objeto del bucket indicado."""
        url = f"{self._storage_root}/object/{bucket}/{ruta.lstrip('/')}"
        headers = self._headers()

        try:
            resp = self._client.delete(url, headers=headers, timeout=10.0)
            return resp.status_code in (200, 204)
        except httpx.HTTPError:
            return False

    def verificar_conexion(self) -> bool:
        """Verifica la alcanzabilidad del servicio de almacenamiento."""
        if not self._key:
            return False
        url = f"{self._storage_root}/bucket"
        headers = self._headers()
        try:
            resp = self._client.get(url, headers=headers, timeout=5.0)
            return resp.status_code in (200, 201)
        except Exception:
            return False


class PublicBucketStorageAdapter(FileStoragePort):
    """Implementación especializada exclusivamente en bucket público."""

    def __init__(self, adapter: SupabaseStorageAdapter | None = None) -> None:
        self._adapter = adapter or SupabaseStorageAdapter()

    def subir_archivo_publico(self, contenido: bytes, ruta_destino: str, tipo_mime: str) -> str:
        return self._adapter.subir_archivo_publico(contenido, ruta_destino, tipo_mime)

    def eliminar_archivo(self, bucket: str, ruta: str) -> bool:
        return self._adapter.eliminar_archivo(bucket, ruta)


class PrivateBucketStorageAdapter:
    """Implementación especializada exclusivamente en bucket privado con URLs firmadas."""

    def __init__(self, adapter: SupabaseStorageAdapter | None = None) -> None:
        self._adapter = adapter or SupabaseStorageAdapter()

    def subir_archivo(self, contenido: bytes, ruta_destino: str, tipo_mime: str) -> str:
        return self._adapter.subir_archivo_privado(contenido, ruta_destino, tipo_mime)

    def obtener_url_firmada(self, ruta_privada: str, segundos_validez: int = 3600) -> str:
        return self._adapter.obtener_url_firmada(ruta_privada, segundos_validez)

    def eliminar_archivo(self, bucket: str, ruta: str) -> bool:
        return self._adapter.eliminar_archivo(bucket, ruta)
