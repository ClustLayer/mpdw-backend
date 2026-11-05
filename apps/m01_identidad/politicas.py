"""Politica de contraseña de HU 04 (RF-AUT-05) y validaciones de usuario (Epic 2)."""

import re
import secrets
import string

from apps.m01_identidad.mensajes import (
    MSG_DOCUMENTO_INVALIDO,
    MSG_PASSWORD_POLITICA,
    MSG_TELEFONO_INVALIDO,
)
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


def documento_valido(documento: str) -> bool:
    valor = (documento or "").strip()
    if not valor or len(valor) > 20:
        return False
    return re.fullmatch(r"[A-Za-z0-9]{6,15}", valor) is not None


def telefono_valido(telefono: str) -> bool:
    valor = (telefono or "").strip()
    if not valor:
        return True
    if len(valor) > 20:
        return False
    return re.fullmatch(r"\+?[0-9]+", valor) is not None


def exigir_documento(documento: str) -> None:
    if not documento_valido(documento):
        raise ReglaNegocioError(MSG_DOCUMENTO_INVALIDO, codigo="DOCUMENTO_INVALIDO")


def exigir_telefono(telefono: str) -> None:
    if not telefono_valido(telefono):
        raise ReglaNegocioError(MSG_TELEFONO_INVALIDO, codigo="TELEFONO_INVALIDO")


def generar_contrasena_inicial(longitud: int = 12) -> str:
    """Genera contraseña temporal alfanumerica con mayuscula, minuscula, numero y especial."""
    if longitud < 12:
        longitud = 12
    especiales = "!@#$%^&*"
    partes = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(especiales),
    ]
    alfabeto = string.ascii_letters + string.digits + especiales
    partes.extend(secrets.choice(alfabeto) for _ in range(longitud - len(partes)))
    secrets.SystemRandom().shuffle(partes)
    clave = "".join(partes)
    validar_politica_password(clave)
    return clave
