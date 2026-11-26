"""Observabilidad: logs generales MongoDB e interacciones analítica (Épica 13 Sprint 4)."""

from apps.m13_plataforma.observability.constants import ACCIONES_SEGURIDAD_SQL
from apps.m13_plataforma.observability.general_log_writer import get_general_log_writer

__all__ = ["ACCIONES_SEGURIDAD_SQL", "get_general_log_writer"]
