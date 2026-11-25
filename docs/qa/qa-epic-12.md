# QA Épica 12 — Eventos y novedades

## API (`/api/v1/eventos/`)

- Listar con `q`, `tipo`, `id_sede`, rango `desde`/`hasta`, `estado`, paginación.
- Crear/editar con tipo (HU + tipos demo), fechas inicio/fin, impacto (Alto/Medio/Bajo), sede opcional (alcance global si nula), áreas afectadas, `visible_sitio`, `imagen_url`, `importancia_clave`.
- Validaciones: campos obligatorios, fin no anterior a inicio, concurrencia `version_fila`.
- Público: `GET /api/v1/eventos/publicos/` (eventos activos y visibles en sitio).
- Sedes activas: `GET /api/v1/eventos/sedes-activas/`.

## Pruebas automatizadas

- `tests/unit/test_epic12_eventos.py`
- Contrato: `docs/openapi.yaml`

## Manual (panel)

- Módulo **Eventos**: listado con filtros demo, modal crear/editar, desactivación con confirmación, badges de impacto/tipo/estado calendario.

## Manual (sitio público)

- Inicio carga eventos desde API; sección Eventos muestra tarjetas con imagen y rango de fechas.
