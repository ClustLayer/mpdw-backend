# Changelog

Versionado del producto: **MAJOR.SPRINT.EPIC_IN_SPRINT** (`1` = major del sistema, `2` = Sprint 2, tercer dígito = épica secuencial del sprint).

| Versión | Alcance |
|---------|---------|
| **1.0.0** | Línea base del backend (arquitectura, salud, contratos) |
| **1.1.1** | Sprint 1 · Épica 1 (autenticación) |
| **1.1.2** | Sprint 1 · Épica 2 (usuarios y perfil) |
| **1.1.3** | Sprint 1 · Épica 3 (roles y permisos) |
| **1.1.4** | Sprint 1 · Épica 4 (sedes) |
| **1.1.5** | Sprint 1 · Cierre (Épicas 13 y 18 + endurecimiento producción) |
| **1.2.1** | Sprint 2 · Épica 5 (catálogo de productos) |
| **1.2.2** | Sprint 2 · Épica 6 (inventario y kardex) |
| **1.2.3** | Sprint 2 · Épica 7 (directorio de clientes y Habeas Data) |
| **1.2.4** | Sprint 2 · Épica 12 (eventos y novedades) |
| **1.2.5** | Sprint 2 · Épica 14 (proveedores e integración inventario) |
| **1.3.1** | Sprint 3 · Épica 8 (punto de venta y facturación) |
| **1.3.2** | Sprint 3 · Épica 9 (domicilios y mensajería) |
| **1.3.3** | Sprint 3 · Épica 10 (facturación electrónica externa — HU 59) |
| **1.3.4** | Sprint 3 · Épica 16 (tienda pública y pedido WhatsApp — HU 88–93) |

---

## 2026-11-20 — v1.3.4 Épica 16 (tienda pública WhatsApp)

- Modelo `Pedidos_web` gestionado; migración `0002_pedidos_web_tabla` (B-2).
- API pública `/api/v1/tienda/` (catálogo, detalle, validación carrito, pedido WhatsApp).
- Slug dinámico de producto y metadatos SEO en detalle (B-9).
- QA: `docs/qa/epic-16.md`; OpenAPI actualizado.

## 2026-11-20 — v1.3.3 Épica 10 (control facturación externa)

- Modelo `Facturas_electronicas`: `url_pdf`, `version_fila` (gestión externa B-7).
- API `/api/v1/ventas/facturacion-externa/` con RBAC `facturacion_electronica`, auditoría `Facturas_gestion_externa`.
- QA: `docs/qa/epic-10.md`; OpenAPI actualizado.

## 2026-11-19 — Iteración 14 (cierre CI épica 9)

- Fix PostgreSQL `FOR UPDATE` en `cambiar_estado` / asignación de domicilios.
- Cobertura unitaria ≥ 90%; tests ampliados épica 8/9 y caja.
- Docs reorganizadas (`docs/qa`, `docs/fixes`, `docs/guides`); ver `docs/fixes/correcciones-iteracion-14-epic9-pos-ventas-domicilios.md`.

## 2026-11-19 — v1.3.2 Épica 9 (domicilios y mensajería) — ampliación POS

- Cuentas bancarias (`/api/v1/caja/cuentas/`) con semilla Nequi/Bancolombia.
- POS: domicilio en emisión, `requiere_domicilio`, transferencias por cuenta.
- OpenAPI actualizado.

## 2026-11-19 — v1.3.2 Épica 9 (domicilios y mensajería)

- Migración `0002_epic9_domicilios`: Entregas, Historial_entregas, Mensajeros ampliados; tipo venta Domicilio.
- API `/api/v1/domicilios/` (bandeja, crear, asignar, estado, mensajeros, historial) con auditoría y transiciones.
- Cálculo al vuelo de antigüedad, duración y años trabajados.
- QA: `docs/qa/epic-9.md`; OpenAPI actualizado.

---

## 2026-11-18 — v1.3.1 Épica 8 (punto de venta y facturación)

- Modelos Pagos, Descuentos_factura, Devoluciones, consecutivos por sede y motor ACID de emisión.
- API `/api/v1/ventas/` (POS, facturas, anulación, devolución).
- QA: `docs/qa/epic-8.md`.

---

## 2026-11-13 — Rendimiento y correcciones (iteración 13)

- Paginación SQL del catálogo, caché en memoria, timeout de cliente, saludo en Bogotá, WhatsApp y matriz sin catálogo editable en la UI.
- Detalle: `docs/fixes/correcciones-iteracion-13.md`.

## 2026-11-12 — Mejoras integrales Sprint 2 (iteración 12)

- Catálogo: `SET_NULL` en categoría, eliminación de parámetros, exportación enriquecida.
- Clientes: color en tipos de cliente; resumen con permisos granulares; eventos con imagen por archivo.
- QA: `docs/fixes/correcciones-iteracion-12.md`, `tests/unit/test_sprint2_mejoras.py`.

## 2026-11-12 — v1.2.5 Épica 14 (proveedores e inventario)

- App `m14_proveedores`, API `/api/v1/proveedores/`, auditoría y concurrencia.
- Inventario: FK `id_proveedor`, purga de kardex de prueba, regla comprado/fabricado.
- QA: `docs/qa/qa-epic-14.md`.

## 2026-11-12 — v1.2.4 Épica 12 (eventos y novedades)

- Modelo y admin `/api/v1/eventos/`, validaciones HU, exposición pública.
- QA: `docs/qa/qa-epic-12.md`.

## 2026-11-12 — v1.2.3 Épica 7 (directorio de clientes y Habeas Data)

- Modelos `Clientes` / `Tipos_cliente` ampliados (apellido, e.164, WhatsApp, ciudad, observaciones, consentimiento, `version_fila`).
- API `/api/v1/clientes/` (CRUD, tipos, verificación de teléfono, historial y métricas).
- Semilla del tipo predeterminado «Común»; `Detalle_factura` para ranking de productos.
- OpenAPI sincronizado; QA en `docs/qa/qa-epic-7.md`.

## 2026-11-11 — v1.2.2 Épica 6 (inventario demo)

- Origen comprado/fabricado en productos; costo unitario en kardex.
- Entrada manual, lote (escaneo/carga rápida) y validación de proveedor.

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
