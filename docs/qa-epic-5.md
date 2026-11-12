# QA — Épica 5 (parámetros y seed)

Ver checklist detallado en `mpdw-frontend/docs/qa-epic-5.md`.

## Backend

- `seed_catalogo_parametros`: cinco tipos base, Vinilos, Diana.
- `accesos-panel`: claves `productos`, `categorias`, `marcas`, `tipos_producto` con mismas acciones.
- `categorias_movimientos` mapea a `categorias_caja` (no compite con categorías de producto).

## Tests

- `tests/unit/test_epic5_catalogo_parametros.py`
