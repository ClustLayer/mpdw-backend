# Correcciones iteración 13 — rendimiento y correcciones funcionales

## Qué se alineó con el código real

El prompt de referencia asumía ViewSets y códigos `productos.ver`. El sistema usa `APIView` y permisos `(modulo, accion)` con `HasDynamicPermission` y la matriz Anexo A. Esa autoridad se conserva. No se renombraron permisos ni se eliminaron overrides por usuario: siguen evaluándose porque las historias y las pruebas los exigen. El catálogo de permisos se quitó solo de la interfaz.

## Cambios

- Listado de productos pagina y filtra stock en SQL (tope 100 en pantalla; exportación hasta 5000).
- Existencias iniciales con `bulk_create`.
- Caché de proceso (`LocMem`) o Redis si existe `REDIS_URL`. La tabla `django_cache` queda sin uso.
- Permisos de rol cacheados 60 s fuera de pruebas e invalidados al guardar la matriz.
- `CONN_MAX_AGE` desde `DB_CONN_MAX_AGE` (60). En pooler Supabase puerto 6543 se mantiene 0.
- Timeout HTTP en el cliente (15 s lectura, 20 s escritura, 60 s archivo).
- El modal de producto cierra al recibir la respuesta del guardado; la imagen no bloquea.
- Saludo del resumen en `America/Bogota`.
- WhatsApp en proveedores y usuarios cuando el número E.164 es válido.
- Código de país del teléfono con ancho mínimo y sin corte.
- Pestaña «Catálogo de permisos» eliminada. Quedan Roles y Matriz.

## Limitaciones

- No se midió latencia real contra Supabase en esta pasada (el conteo de consultas del listado sí tiene prueba).
- Imágenes siguen en disco local y se pierden en un disco efímero.
- LocMem no comparte límites de throttle entre procesos.
- Overrides por usuario siguen activos a propósito.
