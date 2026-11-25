# QA Épica 10 — HU 59 Control de Facturación Externa

## Backend
- `GET /api/v1/ventas/facturacion-externa/` — bandeja (filtros estado, fechas, número; paginación).
- `GET /api/v1/ventas/facturacion-externa/{id}/` — detalle.
- `GET /api/v1/ventas/facturacion-externa/{id}/soporte/` — URL PDF solo si `GENERADA_EXTERNA`.
- `POST /api/v1/ventas/facturacion-externa/{id}/estado/` — cambio manual (permiso Editar).
- Auditoría en entidad `Facturas_gestion_externa`.
- Tests: `test_epic10_facturacion_externa*.py`.

## Frontend
- Ruta `/panel/{rol}/facturacion` — filtros con debounce 300 ms, tabla, detalle, modal de estado, toasts.
- Vitest: `features/facturacion-externa/logic.test.ts`.

## Mensajes literales
- Bandeja vacía / fallo / soporte no disponible según HU 59 CA 5.