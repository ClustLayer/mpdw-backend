# QA Épica 14 — Proveedores e integración con inventario

## API Proveedores (`/api/v1/proveedores/`)

- Listar con `q`, `estado`, paginación (empresa, contacto, teléfono, correo, estado).
- Crear/editar: razón social obligatoria, documento único si se informa, correo validado, teléfono e.164 opcional, auditoría y `version_fila`.
- Selector inventario: `GET /api/v1/proveedores/activos/` y `GET /api/v1/inventario/proveedores-activos/`.

## Inventario (`/api/v1/inventario/`)

- Entrada manual, lote y kardex usan FK `id_proveedor` (proveedor activo).
- Producto **comprado**: `id_proveedor` obligatorio. **Fabricado**: opcional.
- Migración `0004_epic14_proveedor_fk`: purga de movimientos/existencias de prueba y eliminación de `proveedor_nombre`.

## Pruebas automatizadas

- `tests/unit/test_epic14_proveedores.py`
- `tests/unit/test_epic6_inventario.py` (proveedor FK)
- Contrato: `docs/openapi.yaml`

## Manual (panel)

- Módulo **Proveedores**: buscador, filtro activo/inactivo, modales alineados a demo + campos HU.
- **Inventario**: combobox de proveedores en entrada manual, escaneo y carga rápida; kardex muestra nombre del proveedor vinculado.
