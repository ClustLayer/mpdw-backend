# QA Épica 16 — Tienda en línea y pedido por WhatsApp (HU 88–93)

## Backend (`/api/v1/tienda/`, AllowAny)

| Método | Ruta | HU | Descripción |
|--------|------|-----|-------------|
| GET | `filtros/` | 88 | Categorías, marcas y tipos activos |
| GET | `catalogo/` | 88 | Búsqueda, filtros, orden, paginación; solo `estado=true` |
| GET | `productos/{id-slug}/` | 89 | Detalle + metadatos SEO (sin costos ni stock exacto) |
| POST | `carrito/validar/` | 91 | Recalcula precios/disponibilidad (ignora precios cliente) |
| GET | `sedes/` | 92 | Sedes activas con WhatsApp |
| POST | `whatsapp/contacto/` | 93 | URL `wa.me` asesor / sede |
| POST | `pedidos/preparar/` | 92 | Registra `Pedidos_web` PENDIENTE + URL WhatsApp ≤2000 chars |

## Modelo
- `Pedidos_web` managed (B-2): estados PENDIENTE, CONFIRMADO, CANCELADA.
- Slug producto dinámico `{id}-{slug_nombre}` (B-9).

## Tests
- `tests/unit/test_epic16_tienda.py`
- `tests/unit/test_epic16_tienda_api.py`

## Frontend
- Catálogo API, `/producto/:slug`, carrito localStorage, `/carrito/validar`, `/carrito/enviar`.
- Mensajes literales HU en toasts y estados vacío/error.