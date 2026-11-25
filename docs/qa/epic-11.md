# QA — Épica 11 (v1.4.1) — Caja, reporte diario y movimientos

## Alcance
HU 60–79: cuentas bancarias enmascaradas, categorías/conceptos de movimiento, jornada (base inicial, apertura, cuadre, cierre, reapertura), gastos/ahorros/transferencias/adiciones/entregas, historial y exportación, extras clientes import/export y kardex del día sin columnas anterior/nuevo, auditoría sin diff JSON.

## Checklist
- [x] Migración `m08_caja.0004_epic11_caja_movimientos` y permisos demo `m01_identidad.0013_epic11_categorias_caja_demo`.
- [x] API `/api/v1/caja/` (jornada, movimientos, reporte, historial, cuentas).
- [x] Clientes: plantilla, importar y exportar CSV/XLSX en `/api/v1/clientes/`.
- [x] Inventario kardex: sin `cantidad_anterior`/`cantidad_nueva`; filtro día actual por defecto.
- [x] Auditoría: sin `datos_antes`/`datos_despues` en listados.
- [x] Tests `test_epic11_caja.py`, `test_epic11_caja_api.py` y cobertura global ≥ 90 %.
- [x] OpenAPI actualizado (`docs/openapi.yaml`).
- [x] Panel: caja, cierre, conceptos, historial; POS pistola; clientes import/export.

## Prueba manual sugerida
1. Panel **Caja** → registrar gasto y transferencia con referencia.
2. **Cierre de jornada** → cuadre en tiempo real → cerrar con efectivo declarado → reapertura si aplica.
3. **Historial** de arqueos → exportar CSV.
4. **Clientes** → descargar plantilla → importar filas → exportar.
5. **Inventario** → kardex solo hoy; **Auditoría** sin columna diff JSON.