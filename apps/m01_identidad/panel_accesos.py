"""Mapeo módulos Anexo A ↔ claves del panel frontend (HU 18)."""

from apps.m01_identidad.permiso_eval import ACCIONES_CATALOGO
from contratos.catalogos import MATRIZ_ANEXO_A

# Pantallas del catálogo de productos que comparten permisos del dominio catalogo_productos (HU 18 / demo).
CATALOGO_PRODUCTOS_PANEL: tuple[str, ...] = ("productos", "categorias", "marcas", "tipos_producto")

__all__ = [
    "ACCIONES_CATALOGO",
    "CATALOGO_PRODUCTOS_PANEL",
    "MODULOS_CATALOGO",
    "MODULO_A_PANEL",
    "PANEL_A_MODULO",
]

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
    "categorias_movimientos": "categorias_caja",
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
