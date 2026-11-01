# ==============================================================================
# Puerto de Consulta de Sedes - MPDW
# SAD Ref: M02, §6.4
# ==============================================================================
from abc import ABC, abstractmethod


class SedeReadPort(ABC):
    """Puerto expuesto por M02 para validar existencia y estado de sedes."""

    @abstractmethod
    def existe_sede_activa(self, id_sede: int) -> bool:
        """Verifica si una sede existe y está activa."""
        pass

    @abstractmethod
    def listar_ids_sedes_activas(self) -> list[int]:
        """Retorna los identificadores de todas las sedes activas."""
        pass

