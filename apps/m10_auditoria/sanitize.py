# ==============================================================================
# Sanitización de datos sensibles en registros de auditoría (CA 4, HU 82)
# ==============================================================================
from __future__ import annotations

import re
from copy import deepcopy
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "contrasena",
        "contrasena_plana",
        "pin",
        "pin_autorizacion",
        "token",
        "access_token",
        "refresh_token",
        "desafio_token",
        "authorization",
    }
)
_TARJETA_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def _mask_tarjeta_o_cuenta(val: str) -> str:
    """Enmascara secuencias que parecen PAN o números de cuenta largos."""
    s = str(val)
    if len(s) < 13:
        return s
    digits = re.sub(r"\D", "", s)
    if len(digits) >= 13:
        return f"{digits[:4]} **** **** {digits[-4:]}" if len(digits) >= 16 else "[omitido]"
    return s


def _jsonable(val: Any) -> Any:
    """Tipos nativos antes de persistir JSON (time, datetime, Decimal, UUID)."""
    if val is None or isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, time):
        return val.isoformat()
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, (bytes, bytearray)):
        return bytes(val).decode("utf-8", errors="replace")
    if isinstance(val, dict):
        return sanitize_auditoria_payload(val)
    if isinstance(val, (list, tuple)):
        return [
            sanitize_auditoria_payload(x) if isinstance(x, dict) else _jsonable(x) for x in val
        ]
    return str(val)


def _sanitize_value(key: str, val: Any) -> Any:
    lk = str(key).lower()
    if lk in _SENSITIVE_KEYS or "password" in lk or "token" in lk or "pin" in lk:
        return "[omitido]"
    if isinstance(val, str):
        if re.search(_TARJETA_RE, val):
            return _mask_tarjeta_o_cuenta(val)
        return val
    return _jsonable(val)


def sanitize_auditoria_payload(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Copia profunda con campos sensibles sustituidos (no persiste secretos)."""
    if data is None:
        return None
    out: dict[str, Any] = {}
    for k, v in deepcopy(data).items():
        out[k] = _sanitize_value(k, v)
    return out
