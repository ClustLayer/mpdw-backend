"""Transiciones de estado y cálculos al vuelo (Épica 9)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from django.utils import timezone

TRANSICIONES: dict[str, set[str]] = {
    "PENDIENTE": {"ASIGNADO", "CANCELADO"},
    "ASIGNADO": {"EN_CAMINO", "PENDIENTE", "CANCELADO"},
    "EN_CAMINO": {"ENTREGADO", "CANCELADO"},
    "ENTREGADO": set(),
    "CANCELADO": set(),
}

ESTADOS_ETIQUETA = {
    "PENDIENTE": "Pendiente",
    "ASIGNADO": "Asignado",
    "EN_CAMINO": "En ruta",
    "ENTREGADO": "Entregado",
    "CANCELADO": "Cancelado",
}


def transicion_permitida(actual: str, nuevo: str) -> bool:
    return nuevo in TRANSICIONES.get(actual, set())


def transiciones_desde(actual: str) -> list[str]:
    return sorted(TRANSICIONES.get(actual, set()))


def antiguedad_desde(fecha_solicitud: datetime) -> dict[str, Any]:
    ahora = timezone.now()
    if timezone.is_naive(fecha_solicitud):
        fecha_solicitud = timezone.make_aware(fecha_solicitud)
    delta = ahora - fecha_solicitud
    total_min = int(delta.total_seconds() // 60)
    horas, minutos = divmod(total_min, 60)
    alerta = total_min > 60
    return {
        "minutos": total_min,
        "etiqueta": f"{horas}h {minutos}m",
        "alerta_antiguedad": alerta,
    }


def duracion_entrega(entrega: Any) -> str | None:
    inicio = entrega.fecha_solicitud
    fin = entrega.fecha_entrega or entrega.fecha_salida
    if not inicio or not fin:
        return None
    if timezone.is_naive(inicio):
        inicio = timezone.make_aware(inicio)
    if timezone.is_naive(fin):
        fin = timezone.make_aware(fin)
    delta = fin - inicio
    total_min = int(delta.total_seconds() // 60)
    horas, minutos = divmod(total_min, 60)
    return f"{horas}h {minutos}m"


def anos_trabajados(fecha_inicio: date) -> int:
    hoy = timezone.localdate()
    anos = hoy.year - fecha_inicio.year
    if (hoy.month, hoy.day) < (fecha_inicio.month, fecha_inicio.day):
        anos -= 1
    return max(0, anos)
