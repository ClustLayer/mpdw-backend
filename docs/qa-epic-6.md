# QA — Épica 6 Inventario y kardex

## Existencias

- Listado por producto y sede activa, total y mínimo.
- Alerta si alguna sede está en o bajo el mínimo.
- Filtro por nombre/código y sede.

## Movimientos

- Entrada incrementa saldo y deja kardex (`entrada_compra`).
- Ajuste positivo/negativo y merma.
- Traslado resta origen y suma destino; rechaza misma sede o stock insuficiente.
- Historial filtra tipo y fechas.

## Modales (cierre UX)

- `mensajeDe` clona la respuesta: un POST 201 no se interpreta como error al leer el JSON otra vez.
- El diálogo solo tiene un scroll (`overflow-hidden` en `<dialog>`).
- El botón de movimiento muestra spinner y no admite doble clic.

## Automatizado

- `tests/unit/test_epic6_inventario.py`
