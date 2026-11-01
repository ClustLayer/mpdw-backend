# ==============================================================================
# Objetos de Transferencia de Datos (DTOs) y Contextos - MPDW
# SAD Ref: ADR-007, §10.4, §10.9
# ==============================================================================
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class AuthContext:
    """Contexto de autenticación y autorización inyectado en cada petición."""
    id_usuario: int
    email: str
    rol_nombre: str
    sedes_asignadas: tuple[int, ...]
    es_global: bool  # Administrador o Gerente con alcance global
    id_rol: int | None = None
    ip: str = "127.0.0.1"
    user_agent: str = "Unknown"
    id_correlacion: str = ""


@dataclass(frozen=True)
class StockInicialDTO:
    """Stock de apertura por sede al crear un producto (TX-07)."""
    id_sede: int
    cantidad_inicial: Decimal


@dataclass(frozen=True)
class AuditoriaDTO:
    """Datos obligatorios para el registro de auditoría transaccional (ADR-008, G-14)."""
    id_usuario: int | None
    accion: str
    entidad: str
    id_entidad: int
    datos_antes: dict[str, Any] | None
    datos_despues: dict[str, Any] | None
    motivo: str
    resultado: str = "EXITO"
    id_correlacion: str = ""
    ip: str = "127.0.0.1"
    user_agent: str = "Unknown"

