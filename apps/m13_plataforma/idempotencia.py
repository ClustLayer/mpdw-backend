# ==============================================================================
# Utilidad de Idempotencia - MPDW
# SAD Ref: ADR-005, §9.3
# ==============================================================================
from rest_framework.request import Request


class IdempotencyHelper:
    """Extrae y normaliza la clave de idempotencia recibida en la petición."""

    @staticmethod
    def obtener_clave(request: Request) -> str | None:
        clave = request.headers.get("Idempotency-Key")
        if not clave and isinstance(request.data, dict):
            clave = request.data.get("clave_idempotencia")
        if clave:
            return str(clave).strip()
        return None

