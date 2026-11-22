# Épica 11 — Plan de ejecución (HU 60–79, v1.4.1)

## Fase 0 — Auditoría Demo-First

| Demo (`MundoPinturasDiana-Demo`) | Producto (`mpdw-frontend` / API) |
|----------------------------------|----------------------------------|
| `cash-module.tsx` — planilla movimientos, conceptos rápidos, KPI efectivo esperado | `panel-caja-page.tsx` (movimientos día) |
| `cierre-module.tsx` — arqueo, ventas efectivo/transfer, cierre, historial | `panel-cierre-page.tsx` |
| `panel-config.ts` → `caja`, `conceptos`, `cierre`, cuentas | Rutas `caja`, `conceptos`, `cierre`, `panel-cuentas-page` |
| Categorías gasto/transferencia/ahorro/adición | API `Categorias_movimiento` |
| Conceptos frecuentes + valor sugerido | API `Conceptos_movimiento` + botones rápidos |
| Transferencias facturadas bloqueadas | `Transferencias_caja.origen=VENTA`, `editable=false` |

**Brechas resueltas en esta épica:** B-1 (motivo en auditoría vía `motivo`), B-12 (`id_usuario_cierre` / auditoría), B-13 (totales en `Reportes_diarios`), B-14 (catálogos `ESTADO_REPORTE`, tipos movimiento).

## Contrato REST compartido (prefijo `/api/v1/caja/`)

- `GET/POST cuentas/`, `GET/PATCH cuentas/{id}/` — HU 60–61 (número enmascarado en listados)
- `GET/POST categorias/`, `PATCH categorias/{id}/` — HU 62–63
- `GET/POST conceptos/`, `PATCH conceptos/{id}/` — HU 64–65
- `POST jornada/apertura/`, `POST jornada/base-inicial/`, `GET jornada/actual/` — HU 66–67
- `GET/POST movimientos/gastos-ahorros/`, `GET/POST transferencias/`, `POST adiciones/`, `POST entregas/` — HU 68–71
- `POST movimientos/{tipo}/{id}/corregir/`, `POST adjuntos/` — HU 72–73
- `PATCH reporte/venta-registrada/`, `GET reporte/cuadre/`, `POST reporte/cierre/`, `POST reporte/reapertura/` — HU 74–77
- `GET historial/`, `GET historial/export/` — HU 78–79

Errores: `VALIDACION`, `CONCURRENCIA` (409), `JORNADA_CERRADA`, `TRANSFERENCIA_FACTURADA`.

## Orden de commits (backend)

1. `feat(caja): modelos y migración épica 11`
2. `feat(caja): catálogos cuentas categorías conceptos`
3. `feat(caja): apertura base inicial y motor de cuadre`
4. `feat(caja): movimientos transferencias cierre reapertura`
5. `feat(caja): historial exportación pruebas y openapi`
6. `refactor(auditoria): eliminar datos antes/después`
7. `refactor(inventario): kardex día actual sin columnas anterior/nueva`
8. `feat(clientes): importar exportar plantilla`

## Orden de commits (frontend)

1. `feat(caja): UI catálogos y cuentas alineadas demo`
2. `feat(caja): apertura y planilla movimientos`
3. `feat(caja): cierre arqueo y cuadre tiempo real`
4. `feat(caja): historial exportación reapertura`
5. `refactor(inventario): historial día actual`
6. `refactor(auditoria): sin diff json`
7. `feat(clientes): import export`
8. `feat(pos): campo pistola SKU`

## Extras sprint (usuario)

- Clientes: importar / exportar / plantilla (paridad productos)
- POS: modo pistola código barras (paridad inventario)
- Inventario historial: solo día actual por defecto; rango opcional
- Auditoría: sin `datos_anteriores` / `datos_nuevos`