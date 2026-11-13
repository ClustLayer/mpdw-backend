# Rendimiento — listado de productos

| Momento | Comportamiento | Evidencia |
|---|---|---|
| Antes | Hasta 5000 productos en memoria, stock agregado en Python y catálogos en el mismo GET | `AdminCatalogoService.listar` previo a la iteración 13 |
| Después | Página en SQL, máximo 100 filas en pantalla, stock por subconsulta | `test_listado_pagina_en_sql` exige ≤ 8 consultas |

No hay tiempos de red de Supabase en esta tabla: el entorno de medición no ejecutó el baseline contra el pooler. La mejora demostrada es de consultas y de filas materializadas, no de milisegundos de red.
