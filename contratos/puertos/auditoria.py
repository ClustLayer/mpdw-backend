# ==============================================================================
# Puerto de Auditoría Transaccional e Inmutable - MPDW
# SAD Ref: M10, ADR-008, NF-07, G-14
# ==============================================================================
from abc import ABC, abstractmethod

from contratos.dtos import AuditoriaDTO


class AuditPort(ABC):
    """Puerto para registrar evidencias auditables dentro de la misma transacción."""

    @abstractmethod
    def registrar(self, dto: AuditoriaDTO) -> None:
        """Inserta un registro append-only en la bitácora de auditoría."""
        pass

