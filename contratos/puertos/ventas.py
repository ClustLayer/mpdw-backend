# ==============================================================================
# Puerto Inter-Módulo de Lectura de Ventas - MPDW
# SAD Ref: M06, ADR-001, §6.5
# ==============================================================================
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal


class SalesReadPort(ABC):
    """Puerto expuesto por M06 para consultas agregadas requeridas por arqueo."""

    @abstractmethod
    def total_ventas_efectivo_jornada(self, id_sede: int, fecha: date) -> Decimal:
        """Obtiene el total consolidado de ventas cobradas en efectivo."""
        pass

