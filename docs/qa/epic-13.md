# QA Épica 13 — Auditoría, logs Mongo y analítica (Sprint 4 v1.4.2)

- [x] Modelo `Auditoria` reducido a acciones de seguridad en SQL.
- [x] Migración `0004_epic13_auditoria_slim` con respaldo previo a Mongo.
- [x] `AuditService` enruta seguridad → SQL y negocio → log general asíncrono.
- [x] `LOGIN_FALLIDO` en intentos de autenticación fallidos (usuario activo).
- [x] Bitácora filtra solo acciones de seguridad; respuesta sin columnas de entidad.
- [x] `POST /api/v1/analitica/interacciones/` (lote, autenticado).
- [x] Observabilidad `apps/m13_plataforma/observability/` + variables `MONGODB_*`.
- [x] Grafana: `docs/observability/grafana-dashboards.json`, `docs/guides/grafana-sprint4.md`.
- [x] Cobertura unitaria ≥ 90%; OpenAPI regenerado.