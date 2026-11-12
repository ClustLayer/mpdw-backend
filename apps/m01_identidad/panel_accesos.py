"""Mapeo módulos Anexo A ↔ claves del panel frontend (HU 18)."""

from apps.m01_identidad.permiso_eval import ACCIONES_CATALOGO
from contratos.catalogos import MATRIZ_ANEXO_A

__all__ = ["ACCIONES_CATALOGO", "MODULOS_CATALOGO", "MODULO_A_PANEL", "PANEL_A_MODULO"]

MODULO_A_PANEL: dict[str, str] = {
    "autenticacion_perfil": "resumen",
    "usuarios": "usuarios",
    "roles_permisos": "permisos",
    "sedes": "sedes",
    "cuentas_bancarias": "caja",
    "proveedores": "proveedores",
    "catalogo_productos": "productos",
    "inventario_kardex": "inventario",
    "clientes": "clientes",
    "pos": "pos",
    "facturas": "ventas",
    "domicilios": "domicilios",
    "facturacion_electronica": "facturacion",
    "categorias_movimientos": "categorias",
    "gastos_frecuentes": "conceptos",
    "cierre_jornada": "cierre",
    "eventos": "eventos",
    "analitica": "analitica",
    "auditoria": "auditoria",
}

PANEL_A_MODULO: dict[str, str] = {v: k for k, v in MODULO_A_PANEL.items()}

MODULOS_CATALOGO: list[dict[str, str]] = [
    {"clave": modulo, "etiqueta": nombre} for _, modulo, nombre, _, _, _ in MATRIZ_ANEXO_A
]
