# ==============================================================================
# Puerto de Gestión de Transacciones (Unit of Work) - MPDW
# SAD Ref: ADR-005, K-11
# ==============================================================================
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager


class GestorTransaccionPort(ABC):
    """Abstracción para delimitar fronteras transaccionales atómicas."""

    @abstractmethod
    @contextmanager
    def atomic(self) -> Generator[None]:
        """Abre un contexto transaccional atómico local."""
        pass

