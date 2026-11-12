"""Equivalencias de acciones (Total, Sin acceso, Anexo A T/L/O)."""

from __future__ import annotations

ACCIONES_CATALOGO: list[str] = [
    "Crear",
    "Consultar",
    "Editar",
    "Cambiar estado",
    "Anular",
    "Exportar",
    "Sin acceso",
    "Total",
]

_CANDIDATAS: dict[str, tuple[str, ...]] = {
    "T": ("T", "Total"),
    "L": ("L", "Consultar", "Total", "T"),
    "O": ("O", "Total", "T"),
    "Consultar": ("Consultar", "L", "Total", "T"),
    "Crear": ("Crear", "Total", "T"),
    "Editar": ("Editar", "Total", "T"),
    "Cambiar estado": ("Cambiar estado", "Total", "T"),
    "Anular": ("Anular", "Total", "T"),
    "Exportar": ("Exportar", "Consultar", "L", "Total", "T"),
    "Total": ("Total", "T"),
}


def candidatas_para(solicitada: str) -> tuple[str, ...]:
    return _CANDIDATAS.get(solicitada, (solicitada,))
