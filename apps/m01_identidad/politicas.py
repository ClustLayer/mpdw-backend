"""Politica de contraseña de HU 04 (RF-AUT-05)."""

import re

from apps.m01_identidad.mensajes import MSG_PASSWORD_POLITICA
from contratos.excepciones import ReglaNegocioError

_ESPECIALES = set("!@#$%^&*")


def validar_politica_password(password: str, password_actual: str | None = None) -> None:
    """Exige 8 a 64 caracteres, una mayuscula, un numero, un especial y diferencia con la actual."""
    if password_actual is not None and password == password_actual:
        raise ReglaNegocioError(MSG_PASSWORD_POLITICA, codigo="PASSWORD_DEBIL")
    longitud_ok = 8 <= len(password) <= 64
    tiene_mayuscula = any(c.isupper() for c in password)
    tiene_numero = any(c.isdigit() for c in password)
    tiene_especial = any(c in _ESPECIALES for c in password)
    if not (longitud_ok and tiene_mayuscula and tiene_numero and tiene_especial):
        raise ReglaNegocioError(MSG_PASSWORD_POLITICA, codigo="PASSWORD_DEBIL")


def correo_valido(email: str) -> bool:
    if not email or len(email) > 255:
        return False
    return re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", email) is not None
