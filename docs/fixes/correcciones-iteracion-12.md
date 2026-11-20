# Correcciones iteración 12 — Mejoras integrales Sprint 2 (backend)

- `Productos.id_categoria`: `SET_NULL` + migración `0004_producto_categoria_set_null`.
- Parámetros de catálogo: `DELETE` con `eliminar_param()` (tipos base protegidos).
- Exportación: `YYYY-MM-DD-catalogo-productos.{csv,xlsx}` con costo, IVA, categoría, marca, tipo, unidad y origen; alcance por página o filtrado.
- `Tipos_cliente.color` (`#RRGGBB`) con migración y valor por defecto en «Común».
- `GET /api/v1/auth/panel-resumen/`: inventario y actividad reciente según permisos `inventario_kardex` y `auditoria`.
- Eventos: carga de imagen multipart (`POST .../imagen/`) y rutas media en listado público.
- Tests: `tests/unit/test_sprint2_mejoras.py`; cobertura ≥ 90%.
