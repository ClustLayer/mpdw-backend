# ==============================================================================
# Servicios de Clientes - MPDW (Stub Estructural)
# SAD Ref: M05, §6.4
# ==============================================================================
from apps.m05_clientes.repositories import ClienteRepository


class ClienteService:
    """Stub estructural del caso de uso de clientes."""

    def __init__(self, repo: ClienteRepository | None = None) -> None:
        self._repo = repo or ClienteRepository()
