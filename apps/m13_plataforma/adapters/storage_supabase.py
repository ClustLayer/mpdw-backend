# ==============================================================================
# Adaptador Real Supabase Storage (HTTPX) - MPDW
# SAD Ref: ADR-011, I-04, §10.7
# ==============================================================================
import logging

import httpx
from django.conf import settings

from contratos.puertos.almacenamiento import FileStoragePort

logger = logging.getLogger(__name__)


class SupabaseStorageAdapter(FileStoragePort):
    """Adaptador de Supabase Storage para buckets publicos y privados."""

    def __init__(
        self,
        supabase_url: str | None = None,
        service_key: str | None = None,
        bucket_publico: str = "mpdw-public",
        bucket_privado: str = "mpdw-private",
        client: httpx.Client | None = None,
    ) -> None:
        url_val = supabase_url or getattr(settings, "SUPABASE_URL", "http://localhost:54321")
        self._base_url = str(url_val).rstrip("/")
        self._key = str(service_key or getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", ""))
        self._bucket_publico = bucket_publico
        self._bucket_privado = bucket_privado
        self._client = client or httpx.Client(timeout=15.0)

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        return {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": content_type,
        }

    def subir_archivo_publico(self, contenido: bytes, ruta_destino: str, tipo_mime: str) -> str:
        """Sube un archivo al bucket publico y retorna la URL publica."""
        url = (
            f"{self._base_url}/storage/v1/object/{self._bucket_publico}/{ruta_destino.lstrip('/')}"
        )
        headers = self._headers(content_type=tipo_mime)

        try:
            resp = self._client.post(url, content=contenido, headers=headers, timeout=15.0)
            if resp.status_code in (200, 201):
                return f"{self._base_url}/storage/v1/object/public/{self._bucket_publico}/{ruta_destino.lstrip('/')}"
            logger.error("Error al subir a Supabase Storage: %s - %s", resp.status_code, resp.text)
            raise RuntimeError(f"Error en Supabase Storage: {resp.status_code}")
        except httpx.HTTPError as err:
            logger.error("Fallo de red en Supabase Storage: %s", err)
            raise RuntimeError(f"Error de conexion con Supabase Storage: {err}") from err

    def subir_archivo_privado(self, contenido: bytes, ruta_destino: str, tipo_mime: str) -> str:
        """Sube un archivo al bucket privado y retorna la ruta interna."""
        url = (
            f"{self._base_url}/storage/v1/object/{self._bucket_privado}/{ruta_destino.lstrip('/')}"
        )
        headers = self._headers(content_type=tipo_mime)

        try:
            resp = self._client.post(url, content=contenido, headers=headers, timeout=15.0)
            if resp.status_code in (200, 201):
                return ruta_destino
            logger.error("Error al subir archivo privado: %s - %s", resp.status_code, resp.text)
            raise RuntimeError(f"Error en Supabase Storage Privado: {resp.status_code}")
        except httpx.HTTPError as err:
            logger.error("Fallo de red en Supabase Storage Privado: %s", err)
            raise RuntimeError(f"Error de conexion con Supabase Storage: {err}") from err

    def obtener_url_firmada(self, ruta_privada: str, segundos_validez: int = 3600) -> str:
        """Genera una URL firmada de descarga temporal para un objeto privado."""
        url = f"{self._base_url}/storage/v1/object/sign/{self._bucket_privado}/{ruta_privada.lstrip('/')}"
        payload = {"expiresIn": segundos_validez}
        headers = self._headers()

        try:
            resp = self._client.post(url, json=payload, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                signed_path = data.get("signedURL", "")
                return f"{self._base_url}/storage/v1{signed_path}"
            return ""
        except httpx.HTTPError:
            return ""

    def eliminar_archivo(self, bucket: str, ruta: str) -> bool:
        """Elimina un objeto del bucket indicado."""
        url = f"{self._base_url}/storage/v1/object/{bucket}/{ruta.lstrip('/')}"
        headers = self._headers()

        try:
            resp = self._client.delete(url, headers=headers, timeout=10.0)
            return resp.status_code in (200, 204)
        except httpx.HTTPError:
            return False

    def verificar_conexion(self) -> bool:
        """Verifica la alcanzabilidad del servicio de almacenamiento."""
        url = f"{self._base_url}/storage/v1/bucket"
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
