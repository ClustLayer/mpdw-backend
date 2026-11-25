"""Acciones de auditoría que permanecen en PostgreSQL (bitácora de seguridad)."""

from __future__ import annotations

ACCIONES_SEGURIDAD_SQL: frozenset[str] = frozenset(
    {
        "LOGIN_EXITOSO",
        "LOGIN_FALLIDO",
        "CAMBIO_CONTRASENA",
        "CAMBIO_PASSWORD",
    }
)

COLECCION_LOGS_GENERALES = "general_logs"
COLECCION_INTERACCIONES = "interacciones"
