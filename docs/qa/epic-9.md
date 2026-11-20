# QA — Épica 9 (v1.3.2) — Domicilios y mensajería

## Alcance
HU 52–58: crear domicilio, asignar mensajero, cambiar estado, bandeja, CRUD mensajeros, historial.

## Checklist
- [x] Migración `m07_domicilios.0002_epic9_domicilios` (Entregas, Mensajeros, Historial_entregas, tipo venta Domicilio).
- [x] API `/api/v1/domicilios/` con RBAC módulo `domicilios`.
- [x] Antigüedad y duración calculadas en consulta (no persistidas).
- [x] Unicidad entrega activa por factura; transiciones de estado validadas.
- [x] Auditoría en crear domicilio y mensajeros.
- [x] Tests unitarios `test_epic9_domicilios.py`.
- [x] OpenAPI actualizado (`docs/openapi.yaml`).
- [x] Panel `PanelDomiciliosPage` + crear desde factura tipo Domicilio.

## Prueba manual sugerida
1. Emitir factura con tipo **Domicilio** (POS).
2. Detalle factura → **Crear domicilio**.
3. Bandeja → asignar mensajero → **En camino** → **Entregado** (confirmación).
4. Mensajeros → crear/editar; historial con filtros.