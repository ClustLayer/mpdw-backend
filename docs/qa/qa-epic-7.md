# QA Épica 7 — Directorio de clientes y Habeas Data

## API (`/api/v1/clientes/`)

- Listar con `q`, `id_tipo_cliente`, `estado`, paginación.
- Crear/editar con e.164, correo, consentimiento y `fecha_consentimiento` automática.
- Duplicado de teléfono: código `TELEFONO_DUPLICADO` + `confirmar_duplicado`.
- Tipos: CRUD con protección de «Común».
- Historial y métricas (Gerente/Administrador) con `Detalle_factura`.

## Pruebas automatizadas

- `tests/unit/test_epic7_clientes.py`
- Contrato: `docs/openapi.yaml` (`test_openapi_contract`).

## Manual (panel)

- Módulo **Clientes**: listado demo, WhatsApp wa.me, modales, pestaña Tipos, detalle con historial.
