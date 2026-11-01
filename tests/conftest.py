# ==============================================================================
# Fixtures y Configuración de Pruebas - MPDW
# SAD Ref: §14.1, §14.2, Regla R3
# ==============================================================================
from collections.abc import Generator
from contextlib import contextmanager
from decimal import Decimal

import pytest

from contratos.dtos import AuditoriaDTO, AuthContext, StockInicialDTO
from contratos.puertos.auditoria import AuditPort
from contratos.puertos.inventario import InventoryPort
from contratos.puertos.transaccion import GestorTransaccionPort


class FakeTransactionManager(GestorTransaccionPort):
    """Gestor de transacciones en memoria para pruebas unitarias sin I/O."""

    @contextmanager
    def atomic(self) -> Generator[None]:
        yield


class FakeAuditPort(AuditPort):
    """Grabador en memoria de eventos de auditoría para aserciones de prueba."""

    def __init__(self) -> None:
        self.registros: list[AuditoriaDTO] = []

    def registrar(self, dto: AuditoriaDTO) -> None:
        self.registros.append(dto)


class FakeInventoryPort(InventoryPort):
    """Emulador de inventario en memoria."""

    def __init__(self) -> None:
        self.inicializaciones: list[tuple[int, list[StockInicialDTO], str]] = []

    def inicializar_stock_producto(self, id_producto: int, stocks: list[StockInicialDTO], motivo: str) -> None:
        self.inicializaciones.append((id_producto, stocks, motivo))

    def consultar_disponibilidad(self, id_producto: int, id_sede: int) -> Decimal:
        return Decimal("100.00")


@pytest.fixture
def auth_context_admin() -> AuthContext:
    return AuthContext(
        id_usuario=1,
        email="admin@mundopinturasdiana.com",
        rol_nombre="Administrador",
        sedes_asignadas=(1, 2),
        es_global=True,
        ip="127.0.0.1",
        user_agent="pytest-client",
        id_correlacion="test-correlation-id",
    )


@pytest.fixture
def auth_context_empleado() -> AuthContext:
    return AuthContext(
        id_usuario=2,
        email="empleado@mundopinturasdiana.com",
        rol_nombre="Empleado",
        sedes_asignadas=(1,),
        es_global=False,
        ip="127.0.0.1",
        user_agent="pytest-client",
        id_correlacion="test-correlation-id",
    )

