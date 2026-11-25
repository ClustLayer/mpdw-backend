# Iteración 14 — Épica 9 (POS, ventas, domicilios) y cierre CI

Fecha: 2026-11-19

## Backend

- **Domicilios:** `select_for_update()` sin `select_related` en joins externos (PostgreSQL `FOR UPDATE`); transiciones EN_CAMINO/ENTREGADO/CANCELADO; mensajero obligatorio en creación desde POS.
- **Ventas:** emisión POS con bloque domicilio (`id_mensajero`, datos de entrega); `estadisticas_mes` y listado con `vista`; detalle de factura enriquecido para impresión.
- **Caja:** API CRUD cuentas bancarias y listado activas.
- **Tests:** ampliación `test_epic9_domicilios*`, `test_epic8_ventas`, `test_caja_*`; cobertura unitaria ≥ 90%.
- **Calidad:** ruff/mypy/import-linter; OpenAPI alineado (`test_openapi_contract`).

## Frontend

- **POS:** selector de mensajero y campos domicilio al marcar venta domicilio.
- **Ventas:** tarjetas demo, tabla, estadísticas del mes, rutas de impresión carta/térmica.
- **Domicilios:** vista demo (en ruta, entregado, cancelar) y bandejas por `vista`.
- **Calidad:** ESLint sin errores, typecheck, Vitest y build.

## Documentación

- Reorganización `docs/qa`, `docs/fixes`, `docs/guides` (backend y frontend).

## Puertas CI

| Puerta | Backend | Frontend |
|--------|---------|----------|
| 0–4 | Secretos, ruff, mypy, imports, pytest unit ≥90% | ESLint, typecheck, Vitest |
| 5–9 | Integración Postgres, OpenAPI diff, bandit, pip-audit, Docker | Build, Playwright e2e |

Puerta 5 backend requiere PostgreSQL (`MPDW_TEST_USE_POSTGRES=true`), como en GitHub Actions.