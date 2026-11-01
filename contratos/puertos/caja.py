# ==============================================================================
# Puerto Inter-Módulo de Caja - MPDW
# SAD Ref: M08, ADR-001, §6.5
# ==============================================================================
from abc import ABC, abstractmethod


class CashPort(ABC):
    """Puerto expuesto por M08 para consultar estado de jornada y precargar transferencias."""

    @abstractmethod
    def jornada_esta_abierta(self, id_sede: int) -> bool:
        """Indica si existe una jornada de caja abierta en la sede dada."""
        pass

