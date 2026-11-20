# QA manual — Cierre Sprint 1 (Épicas 13 y 18)

**Versión:** 1.1.5  
**Fecha:** 2026-11-06  
**Ramas:** `epica-13-18-cierre-sprint1` (backend y frontend)

## Preparación

1. Aplicar migraciones en Supabase/local: `python manage.py migrate` (desde `mpdw-backend`).
2. Variables: backend `.env` con PostgreSQL; frontend `.env` con `VITE_API_URL`.
3. Reiniciar API y Vite (`pnpm dev` o `npm exec pnpm@10.15.0 dev`) tras migraciones.

## Épica 13 — HU 82 Bitácora de auditoría

| ID | Caso | Pasos | Esperado |
|----|------|-------|----------|
| E13-01 | Acceso admin | Iniciar como administrador → Panel → Auditoría | Se muestra la pantalla de bitácora. |
| E13-02 | Acceso gerente con permiso | Usuario gerente con permiso Consultar en auditoría | Solo lectura, misma UI. |
| E13-03 | Sin permiso | Usuario sin permiso al módulo | Mensaje de acceso denegado (texto transversal). |
| E13-04 | Filtros combinables | Usuario (búsqueda), acción, entidad, id entidad, fechas válidas → Aplicar | Lista filtrada; fecha inicial ≤ fecha final. |
| E13-05 | Paginación | `page` / `page_size` en URL o UI | Respuesta paginada; mensaje "Mostrando n de total…" o vacío CA. |
| E13-06 | Detalle | Abrir detalle de una fila | `datos_anteriores` / `datos_nuevos` visibles; cambios resaltados. |
| E13-07 | Error carga | API caída o 500 simulado | Toast y mensaje "No fue posible cargar la bitácora…" |
| E13-08 | Inmutabilidad API | Intentar POST/PUT/PATCH a bitácora (si existiera ruta) | No expuesto / 405 según contrato. |

## Épica 18 — HU 96 Confirmación destructiva

| ID | Caso | Pasos | Esperado |
|----|------|-------|----------|
| E18-01 | Diálogo | Desactivar usuario con motivo obligatorio | Título, mensaje con nombre de registro, motivo ≤255, Confirmar/Cancelar. |
| E18-02 | Cancelar | Cancelar o Escape o clic fuera | Sin cambios en servidor. |
| E18-03 | Doble clic | Confirmar dos veces rápido | Un solo envío (busy en botón). |
| E18-04 | Foco | Tab dentro del modal | Foco atrapado; al cerrar vuelve al disparador. |

## Épica 18 — HU 97 Conflicto de edición

| ID | Caso | Pasos | Esperado |
|----|------|-------|----------|
| E18-10 | 409 | Editar mismo usuario en dos sesiones; guardar el segundo primero | Primer guardado muestra diálogo de conflicto (mensaje HU). |
| E18-11 | Recargar | "Recargar versión actual" | Datos frescos; toast de éxito según HU. |
| E18-12 | Borrador | Tras 409 | Borrador en `sessionStorage` hasta decidir. |

## Automatización local

- Backend: `make calidad` (9 puertas).
- Frontend: `pnpm run calidad` (o `npx pnpm@10.15.0 run calidad` si `pnpm` no está en PATH). Primera vez: `npx playwright install chromium`.

## Cierre

- [ ] Migraciones aplicadas en Supabase.
- [ ] API y frontend reiniciados tras migrate.
