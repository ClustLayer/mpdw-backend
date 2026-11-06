"""Filas de matriz agrupadas por módulo del panel (una fila por pantalla)."""

from __future__ import annotations

from apps.m01_identidad.permiso_eval import ACCIONES_CATALOGO

# panel_key, módulo dominio (Anexo A), etiqueta UI
PANEL_MATRIZ_ORDEN: list[tuple[str, str, str]] = [
    ("resumen", "autenticacion_perfil", "Resumen"),
    ("usuarios", "usuarios", "Usuarios"),
    ("permisos", "roles_permisos", "Permisos"),
    ("sedes", "sedes", "Sedes"),
    ("categorias", "catalogo_productos", "Categorías de producto"),
    ("productos", "catalogo_productos", "Productos"),
    ("inventario", "inventario_kardex", "Inventario"),
    ("clientes", "clientes", "Clientes"),
    ("proveedores", "proveedores", "Proveedores"),
    ("ventas", "facturas", "Ventas"),
    ("pos", "pos", "Punto de venta"),
    ("domicilios", "domicilios", "Domicilios"),
    ("facturacion", "facturacion_electronica", "Factura electrónica"),
    ("caja", "cuentas_bancarias", "Caja"),
    ("conceptos", "gastos_frecuentes", "Conceptos de caja"),
    ("cierre", "cierre_jornada", "Cierre de jornada"),
    ("eventos", "eventos", "Eventos"),
    ("promociones", "eventos", "Promociones y sorteos"),
    ("auditoria", "auditoria", "Auditoría"),
    ("analitica", "analitica", "Analítica"),
]

__all__ = ["ACCIONES_CATALOGO", "PANEL_MATRIZ_ORDEN"]
