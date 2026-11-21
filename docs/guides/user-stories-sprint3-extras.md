# User stories — Sprint 3 (extras)

| ID | Prioridad | Historia |
|----|-----------|----------|
| S3-01 | Alta | Como **administrador**, quiero ver en el **resumen** ventas del día, domicilios pendientes y facturas electrónicas pendientes con datos reales, para decidir acciones sin entrar a cada módulo. |
| S3-02 | Alta | Como **administrador**, quiero **alertas de inventario** con los cinco productos de menor stock y un enlace a inventario, para reponer a tiempo. |
| S3-03 | Alta | Como **administrador**, quiero gestionar **vitrinas del inicio** (título, frase, productos, estado y enlace al catálogo), para que el sitio público refleje la demo. |
| S3-04 | Media | Como **visitante**, quiero ver en **inicio** productos y carruseles desde la API, para navegar sin esperas innecesarias. |
| S3-05 | Media | Como **comprador web**, quiero un **mensaje de pedido WhatsApp** legible y un selector de país **+57** por defecto, para confirmar pedidos sin errores de formato. |
| S3-06 | Media | Como **administrador de catálogo**, quiero **colores por producto** en la tienda y vitrinas administrables, para vender vinilos por tonalidad como en la demo. |
| S3-07 | Media | Como **administrador**, quiero **activar/desactivar cuentas bancarias** en el panel de caja, para controlar qué cuentas aparecen en el POS. |
| S3-08 | Baja | Como **usuario del panel**, quiero **notificaciones unificadas** arriba a la derecha con cierre en ×, para no confundir avisos con el estilo antiguo. |

**Backend:** tablas `Escaparate_seccion`, `Escaparate_producto`, `Colores_catalogo`, `Productos_colores`, `Cuentas_bancarias` (caja), endpoints `/api/v1/auth/panel-resumen`, `/api/v1/tienda/escaparates/`, `/api/v1/catalogo/escaparates/`.