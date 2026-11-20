"""Estados y etiquetas — gestión externa de facturación electrónica."""

ESTADOS_FILTRO = ("PENDIENTE", "GENERADA_EXTERNA", "CANCELADA")

ESTADOS_ETIQUETA: dict[str, str] = {
    "PENDIENTE": "Pendiente",
    "GENERADA_EXTERNA": "Generada Externamente",
    "CANCELADA": "Cancelada",
}


def transicion_permitida(actual: str, nuevo: str) -> bool:
    if actual == nuevo:
        return True
    if actual == "PENDIENTE" and nuevo in ("GENERADA_EXTERNA", "CANCELADA"):
        return True
    return False
