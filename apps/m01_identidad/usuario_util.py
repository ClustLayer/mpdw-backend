"""Utilidades de presentacion y auditoria para usuarios (Epic 2)."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.utils import timezone

from apps.m01_identidad.models import Usuario_sede, Usuarios


def _fecha_iso(valor: date | None) -> str | None:
    return valor.isoformat() if valor is not None else None


def nombre_completo(usuario: Usuarios) -> str:
    partes = [usuario.nombre.strip(), getattr(usuario, "apellido", "").strip()]
    texto = " ".join(p for p in partes if p)
    return texto or usuario.email


def estado_etiqueta(usuario: Usuarios) -> str:
    if usuario.bloqueado_hasta and usuario.bloqueado_hasta > timezone.now():
        return "Bloqueado"
    if not usuario.estado:
        return "Inactivo"
    return "Activo"


def snapshot_usuario(usuario: Usuarios, *, incluir_sedes: bool = True) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id_usuario": usuario.id_usuario,
        "nombre": usuario.nombre,
        "apellido": getattr(usuario, "apellido", ""),
        "documento": usuario.documento,
        "telefono": getattr(usuario, "telefono", ""),
        "tipo_sangre": getattr(usuario, "tipo_sangre", ""),
        "fecha_nacimiento": _fecha_iso(getattr(usuario, "fecha_nacimiento", None)),
        "direccion": getattr(usuario, "direccion", ""),
        "contacto_emergencia_nombre": getattr(usuario, "contacto_emergencia_nombre", ""),
        "contacto_emergencia_telefono": getattr(usuario, "contacto_emergencia_telefono", ""),
        "email": usuario.email,
        "id_rol": usuario.id_rol_id,
        "rol": usuario.id_rol.nombre if usuario.id_rol_id else None,
        "estado": usuario.estado,
        "estado_etiqueta": estado_etiqueta(usuario),
        "version_fila": int(getattr(usuario, "version_fila", 1) or 1),
    }
    if incluir_sedes:
        data["sedes"] = [
            {"id_sede": s.id_sede_id, "es_principal": s.es_principal}
            for s in Usuario_sede.objects.filter(id_usuario=usuario, estado=True).order_by(
                "id_sede_id"
            )
        ]
    return data
