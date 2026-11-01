# ==============================================================================
# Puerto Inter-Módulo de Inventario - MPDW
# SAD Ref: M04, ADR-001, PR-3, TX-07
# ==============================================================================
from abc import ABC, abstractmethod
from decimal import Decimal

from contratos.dtos import StockInicialDTO


class InventoryPort(ABC):
    """Puerto expuesto por M04 para operaciones de stock solicitadas por otros módulos."""

    @abstractmethod
    def inicializar_stock_producto(
        self,
        id_producto: int,
        stocks: list[StockInicialDTO],
        motivo: str,
    ) -> None:
        """Crea filas de inventario inicial en las sedes indicadas (TX-07)."""
        pass

    @abstractmethod
    def consultar_disponibilidad(self, id_producto: int, id_sede: int) -> Decimal:
        """Consulta la cantidad disponible de un producto en una sede."""
        pass

