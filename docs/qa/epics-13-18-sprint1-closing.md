# QA — Épicas 13 y 18 (Cierre Sprint 1) · v1.1.5

**Fecha:** 2026-11-06  
**Rama:** `epica-13-18-cierre-sprint1`

## Preparación

1. `python manage.py migrate --noinput`
2. `python manage.py createcachetable`
3. `.env` con `DATABASE_URL` del pooler (`postgres.<PROJECT_REF>@…pooler.supabase.com`).
4. Reiniciar API tras migraciones.

## Épica 13 — HU 82 Bitácora

| ID | Caso | Esperado |
|----|------|----------|
| E13-01 | Admin / gerente con Consultar | Acceso a bitácora |
| E13-02 | Buscador general `q` | Filtra entidad, id o usuario |
| E13-03 | Combobox Acción | Filtra por acción exacta |
| E13-04 | Detalle | Diff de datos anteriores/nuevos |
| E13-05 | Sin resultados / error | Mensajes CA literales |
| E13-06 | Mutaciones API | No hay escritura sobre bitácora |

## Épica 18 — HU 96 / 97

| ID | Caso | Esperado |
|----|------|----------|
| E18-01 | Confirmación destructiva | Modal + motivo ≤255 |
| E18-02 | Cancelar / Escape | Sin cambios |
| E18-03 | Conflicto 409 | Diálogo recargar/cancelar |

## Sedes / producción (iteración v1.1.5)

| ID | Caso | Esperado |
|----|------|----------|
| S-01 | Desactivar desde Acciones | Modal + PATCH; desaparece de `/api/v1/branches/` |
| S-02 | Marcar `es_principal` | Solo una sede principal |
| S-03 | Login con pooler | Sin 500 por throttle/caché |
| S-04 | `createcachetable` | Tabla `django_cache` presente |

## Automatizado

```bash
make calidad
```
