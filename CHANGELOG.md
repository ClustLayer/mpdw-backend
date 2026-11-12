# Changelog

Versionado del producto (**major.sprint.epica**):

| Versión | Alcance |
|---------|---------|
| **1.0.0** | Línea base del backend (arquitectura, salud, contratos) |
| **1.1.1** | Sprint 1 · Épica 1 (autenticación) |
| **1.1.2** | Sprint 1 · Épica 2 (usuarios y perfil) |
| **1.1.3** | Sprint 1 · Épica 3 (roles y permisos) |
| **1.1.4** | Sprint 1 · Épica 4 (sedes) |
| **1.1.5** | Sprint 1 · Cierre (Épicas 13 y 18 + endurecimiento producción) |
| **1.2.6** | Sprint 2 · Épica 6 (inventario y kardex) |

---

## 2026-11-06 — v1.1.5 Cierre Sprint 1 (Épicas 13 y 18 + producción)

### Funcional
- Bitácora de auditoría (HU 82): listado filtrable, paginación validada, sanitización de secretos, buscador libre `q` y catálogo de acciones.
- Concurrencia optimista unificada (`ConflictoVersionError` → HTTP 409) y motivo en operaciones críticas.
- Sedes: campo `es_principal` (única), desactivación sin romper auditoría JSON, snapshots con tipos nativos (`time`/`Decimal`/`UUID`).

### Producción / estabilidad
- Parsing de `DATABASE_URL` con `dj-database-url`; conserva usuario `postgres.<PROJECT_REF>` del pooler Supabase.
- `DISABLE_SERVER_SIDE_CURSORS`, `prepare_threshold=None` y SSL (`sslmode=require`) en producción.
- Throttle DRF degradado ante `OperationalError`/`DatabaseError` (sin 500 en login).
- Release: `migrate` + `createcachetable` documentados.

---

## 2026-11-05 — v1.1.4 Épica 4 (sedes)

- Gestión administrativa de sedes, horarios, consolidado y listado público `/api/v1/branches/`.
- Endurecimiento RBAC asociado al módulo sedes.

## 2026-11-05 — v1.1.3 Épica 3 (roles y permisos)

- Roles, catálogo de permisos, matriz de autorización y seeds de demo.
- Purge de permisos legacy y ajustes de vistas admin.

## 2026-11-05 — v1.1.2 Épica 2 (usuarios y perfil)

- CRUD administrativo de usuarios, cambio de estado, contraseña temporal y Mi perfil.
- Concurrencia optimista en edición; auditoría de mutaciones.

## 2026-11-04 — v1.1.1 Épica 1 (autenticación)

- Login, logout, recuperación, cambio de contraseña, refresh con rotación y 2FA admin.
- Auditoría de autenticación sin persistir secretos.

## 2026-10 — v1.0.0 Línea base

- Arquitectura modular M01–M13, contratos OpenAPI, health checks, pipeline `make calidad`.
