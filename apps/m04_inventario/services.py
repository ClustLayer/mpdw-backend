# ==============================================================================
# Servicio de Inventario y Kardex - MPDW
# SAD Ref: M04, ADR-001, ADR-005, §6.5, BR-06, BR-07, TX-07
# ==============================================================================
from decimal import Decimal

from apps.m04_inventario.repositories import InventarioRepository, MovimientoInventarioRepository
from contratos.catalogos import TipoMovimientoInventario
from contratos.dtos import StockInicialDTO
from contratos.puertos.inventario import InventoryPort


class InventarioService(InventoryPort):
    """
    Servicio de dominio de Inventario que implementa el puerto contractual InventoryPort
    para consumo inter-módulos (SAD §6.5, ADR-001). Coordina la persistencia a través
    de InventarioRepository y MovimientoInventarioRepository.
    """

    def __init__(
        self,
        inv_repo: InventarioRepository | None = None,
        mov_repo: MovimientoInventarioRepository | None = None,
    ) -> None:
        self._inv_repo = inv_repo or InventarioRepository()
        self._mov_repo = mov_repo or MovimientoInventarioRepository()

    def inicializar_stock_producto(
        self,
        id_producto: int,
        stocks: list[StockInicialDTO],
        motivo: str,
    ) -> None:
        """Inicializa existencias en múltiples sedes y registra movimientos de entrada (TX-07)."""
        for stock_dto in stocks:
            inv = self._inv_repo.obtener_o_crear(
                id_producto=id_producto,
                id_sede=stock_dto.id_sede,
                cantidad_inicial=stock_dto.cantidad_inicial,
            )
            if stock_dto.cantidad_inicial > Decimal("0.00"):
                self._mov_repo.registrar_movimiento(
                    id_inventario=inv.id_inventario,
                    tipo_movimiento=TipoMovimientoInventario.ENTRADA,
                    cantidad=stock_dto.cantidad_inicial,
                    cantidad_anterior=Decimal("0.00"),
                    cantidad_nueva=stock_dto.cantidad_inicial,
                    motivo=motivo,
                )

    def consultar_disponibilidad(self, id_producto: int, id_sede: int) -> Decimal:
        """Consulta existencia física disponible en una sede específica."""
        return self._inv_repo.consultar_stock(id_producto, id_sede)

    def consultar_stock(self, id_producto: int, id_sede: int) -> Decimal:
        """Alias de conveniencia para consultar existencia."""
        return self.consultar_disponibilidad(id_producto, id_sede)
