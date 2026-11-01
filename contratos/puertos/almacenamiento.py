# ==============================================================================
# Puerto de Almacenamiento de Archivos (Supabase Storage) - MPDW
# SAD Ref: ADR-011, I-04
# ==============================================================================
from abc import ABC, abstractmethod


class FileStoragePort(ABC):
    """Puerto de borde para subida y eliminación de medios y adjuntos."""

    @abstractmethod
    def subir_archivo_publico(self, contenido: bytes, ruta_destino: str, tipo_mime: str) -> str:
        """Sube un archivo al bucket público y retorna la URL pública."""
        pass

    @abstractmethod
    def eliminar_archivo(self, bucket: str, ruta: str) -> bool:
        """Elimina un archivo del bucket correspondiente (limpieza de huérfanos)."""
        pass

