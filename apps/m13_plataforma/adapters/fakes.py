# ==============================================================================
# Fakes para Pruebas Unitarias de Adaptadores Externos - MPDW
# SAD Ref: ADR-011, E-02
# ==============================================================================
from contratos.puertos.almacenamiento import FileStoragePort
from contratos.puertos.correo import EmailPort


class FakeEmailAdapter(EmailPort):
    def __init__(self) -> None:
        self.enviados: list[dict[str, str]] = []

    def enviar_recuperacion_password(self, destinatario: str, enlace: str) -> bool:
        self.enviados.append({"destinatario": destinatario, "enlace": enlace})
        return True

    def enviar_codigo_2fa(self, destinatario: str, codigo: str) -> bool:
        self.enviados.append({"destinatario": destinatario, "codigo": codigo})
        return True


class FakeStorageAdapter(FileStoragePort):
    def __init__(self) -> None:
        self.archivos: dict[str, bytes] = {}

    def subir_archivo_publico(self, contenido: bytes, ruta_destino: str, tipo_mime: str) -> str:
        self.archivos[ruta_destino] = contenido
        return f"https://fake-storage.local/{ruta_destino}"

    def eliminar_archivo(self, bucket: str, ruta: str) -> bool:
        if ruta in self.archivos:
            del self.archivos[ruta]
            return True
        return False

