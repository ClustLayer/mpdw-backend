# QA Épica 8 — Punto de venta y facturación (backend)

## POS (`/api/v1/ventas/pos/`)

- Catálogos: sedes, tipos de venta, métodos Efectivo/Transferencia.
- Búsqueda productos activos con stock por sede (≤ 1 s).
- Emisión ACID: factura + detalle + pagos + kardex + FE opcional + consecutivo.

## Facturas (`/api/v1/ventas/facturas/`)

- Listado con filtros, margen negativo (gerente/admin).
- Detalle, anulación con motivo ≥ 10 caracteres, devolución parcial, edición admin.

## Pruebas automatizadas

- `tests/unit/test_epic8_ventas.py`
- `make calidad` (cobertura ≥ 90%)