# User stories

## HU_MPDW_01_01 — Iniciar sesion
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero autenticar mis credenciales (correo electronico y contraseña) en el sistema, para acceder unicamente a los modulos que mi rol autoriza y proteger la informacion del negocio.

### Criterios de aceptacion
1. La accion se realiza en la pantalla "Iniciar sesion".
2. Correo electronico obligatorio, maximo 255, formato valido. Mensaje: "El correo electronico ingresado no tiene un formato valido."
3. Contraseña obligatoria, oculta por defecto, con boton de visualizacion. Mensaje: "La contraseña es obligatoria."
4. El boton "Iniciar sesion" permanece inhabilitado mientras correo o contraseña esten vacios.
5. Si el usuario existe, esta activo, no tiene bloqueo vigente y la contraseña coincide con el hash, se crea la sesion, intentos_fallidos vuelve a 0, se actualiza ultimo_acceso y se redirige al inicio del rol. Si debe_cambiar_password, primero va a cambiar contraseña. Si el administrador tiene 2FA, va a la verificacion.
6. La contraseña no se guarda ni viaja en claro. Access token 15 minutos y refresh token 7 dias, ambos configurables. El refresh se guarda como hash. Los tokens no van en la URL ni en los logs.
7. Exito: "Bienvenido(a), {nombre}."
8. Credenciales, inactivo o contraseña incorrecta: "Credenciales no validas, por favor intente de nuevo." A los 5 intentos: "Acceso temporalmente bloqueado. Intente mas tarde o contacte al administrador."
9. Error no anticipado: "No fue posible iniciar sesion. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_02 — Cerrar sesion
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero cerrar mi sesion activa, para evitar que otra persona use mi cuenta en un equipo compartido.

### Criterios de aceptacion
1. La opcion "Cerrar sesion" esta en el menu de usuario de toda pantalla autenticada.
2. No captura datos y esta habilitada con sesion activa.
3. Revoca el refresh token (`fecha_revocacion`), invalida el access token, limpia el estado local y redirige a "Iniciar sesion".
4. Un token revocado no renueva la sesion (401). Tras el cierre, el boton Atras no deja ver rutas protegidas.
5. Exito: "Sesion cerrada correctamente."
6. Sesion ya expirada: "Su sesion ya habia expirado. Inicie sesion nuevamente."
7. Fallo de revocacion: "No fue posible cerrar la sesion en el servidor. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_03 — Recuperar contraseña
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero restablecer mi contraseña olvidada mediante un enlace temporal de un solo uso, para recuperar el acceso a mi cuenta sin depender del administrador.

### Criterios de aceptacion
1. Pantallas "Recuperar contraseña" y "Nueva contraseña".
2. Correo obligatorio. Boton "Enviar enlace" inhabilitado si esta vacio.
3. Nueva contraseña y confirmacion cumplen la politica de HU 04 y deben coincidir.
4. La respuesta al solicitar el enlace es siempre la misma, exista o no la cuenta.
5. El enlace dura 60 minutos, se guarda solo como hash, es de un solo uso y al usarse revoca las sesiones.
6. Exito de solicitud: "Si el correo esta registrado, recibira un enlace para restablecer su contraseña."
7. Exito de restablecimiento: "Su contraseña ha sido restablecida. Ya puede iniciar sesion."
8. Enlace invalido: "El enlace de recuperacion no es valido o ha expirado. Solicite uno nuevo."
9. Error no anticipado: "No fue posible completar la solicitud. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_04 — Cambiar contraseña
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero cambiar mi contraseña validando la contraseña actual, para mantener segura mi cuenta y cumplir el cambio obligatorio cuando se me asigne una contraseña temporal.

### Criterios de aceptacion
1. Pantalla "Cambiar contraseña", obligatoria si `debe_cambiar_password` es verdadero.
2. Contraseña actual, nueva y confirmacion. La nueva exige mayuscula, numero, caracter especial `!@#$%^&*` y longitud de 8 a 64, y debe ser distinta de la actual.
3. "Guardar contraseña" inhabilitado si falta un campo. "Cancelar" no aparece cuando el cambio es obligatorio.
4. Campos vacios: "Todos los campos obligatorios deben ser diligenciados."
5. Actual incorrecta: "La contraseña actual es incorrecta."
6. Politica: "La contraseña no cumple los requisitos minimos de seguridad."
7. Confirmacion distinta: "Las contraseñas no coinciden."
8. Se guarda solo el hash, `debe_cambiar_password` pasa a falso y la auditoria no guarda la contraseña.
9. Exito: "Su contraseña ha sido actualizada correctamente."
10. Error no anticipado: "No fue posible cambiar la contraseña. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_05 — Continuidad de sesion
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero continuar mi sesion cuando el sistema me avise de su proxima expiracion por inactividad, para no perder el trabajo en curso.

### Criterios de aceptacion
1. Dialogo modal sobre cualquier pantalla autenticada.
2. Cuenta regresiva, boton "Continuar sesion" y boton "Cerrar sesion".
3. Inactividad por defecto de 60 minutos y aviso 5 minutos antes. Ambos vienen de la configuracion.
4. Continuar renueva los tokens con rotacion del refresh. Un refresh ya rotado revoca la familia.
5. Ante 401 el cliente intenta una sola renovacion.
6. Exito: "Su sesion continua activa."
7. Tiempo agotado: "Su sesion expiro por inactividad. Inicie sesion nuevamente."
8. Fallo tecnico: "No fue posible renovar la sesion. Inicie sesion nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_06 — Verificacion en dos pasos
**Historia de usuario:** Yo como administrador, quiero verificar mi identidad con un codigo de segundo paso al iniciar sesion, para proteger con una capa adicional la cuenta de mayores privilegios.

### Criterios de aceptacion
1. La pantalla aparece despues del login solo si el 2FA del administrador esta habilitado.
2. Codigo numerico de 6 digitos. Boton "Verificar" inhabilitado si esta vacio.
3. "Reenviar codigo" invalida el anterior.
4. El codigo se guarda solo como hash, dura 10 minutos y admite 3 intentos.
5. Exito: "Verificacion completada."
6. Codigo incorrecto: "El codigo ingresado no es valido."
7. Expirado o usado: "El codigo ha expirado. Solicite uno nuevo."
8. Error no anticipado: "No fue posible verificar el codigo. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_07 — Crear usuario
**Status:** COMPLETED — **Received:** 2026-11-05

## HU_MPDW_01_08 — Listado de usuarios
**Status:** COMPLETED — **Received:** 2026-11-05

## HU_MPDW_01_09 — Editar usuario
**Status:** COMPLETED — **Received:** 2026-11-05

## HU_MPDW_01_10 — Cambiar estado
**Status:** COMPLETED — **Received:** 2026-11-05

## HU_MPDW_01_11 — Generar contraseña temporal
**Status:** COMPLETED — **Received:** 2026-11-05

## HU_MPDW_01_12 — Mi perfil
**Status:** COMPLETED — **Received:** 2026-11-05

## Epica 3 — Roles, permisos y control de acceso (2026-11-05)

| Historia | Estado | Evidencia |
|----------|--------|-----------|
| HU_MPDW_01_13 Crear rol / listado | COMPLETED | `POST/GET /api/v1/roles-permisos/roles`, tests `test_epic3_*` |
| HU_MPDW_01_14 Editar rol | COMPLETED | `PATCH /api/v1/roles-permisos/roles/{id}` |
| HU_MPDW_01_15 Crear permiso / catálogo | COMPLETED | `POST/GET /api/v1/roles-permisos/permisos` |
| HU_MPDW_01_16 Editar permiso | COMPLETED | `PATCH /api/v1/roles-permisos/permisos/{id}` |
| HU_MPDW_01_17 Matriz de permisos | COMPLETED | `GET/PUT /api/v1/roles-permisos/matriz` |
| HU_MPDW_01_18 Rutas y menú autorizados | COMPLETED | `GET /api/v1/auth/accesos-panel`, `PermissionService.accesos_panel` |

Migración: `0008_epic3_roles_permisos`. OpenAPI: `docs/openapi.yaml`.

## Epica 4 — Sedes (2026-11-05)

| Historia | Estado | Evidencia |
|----------|--------|-----------|
| HU_MPDW_01_19 Crear sede | COMPLETED | `POST /api/v1/sedes/gestion/` |
| HU_MPDW_01_20 Editar / desactivar sede | COMPLETED | `PATCH /api/v1/sedes/gestion/{id}/` |
| HU_MPDW_01_21 Consolidado por sede | PARTIAL | `GET /api/v1/sedes/consolidado/` (estructura; agregados cuando haya datos) |

Migraciones: `0002_epic4_sedes_horarios`, permisos demo `0009`/`0010`, seed `0003`. Iteraciones 8–9 en `docs/correcciones-iteracion-*.md`.

## Épica 13 — Auditoría y trazabilidad (2026-11-06) — **v1.1.5**

| Historia | Estado | Evidencia |
|----------|--------|-----------|
| HU_MPDW_01_82 Bitácora de auditoría | COMPLETED | `GET /api/v1/auditoria/bitacora/`, `GET /api/v1/auditoria/bitacora/usuarios/`, `BitacoraAuditoriaService`, `sanitize.py`, migración `0002_ep13_auditoria_campos`, permiso gerente `0011_gerente_auditoria_consultar` |

## Épica 18 — Comportamientos transversales (2026-11-06) — **v1.1.5**

- **HU 96 / 97 (API y dominio):** revalidación de permisos en servidor; HTTP 409 ante conflicto de versión; motivo obligatorio en cambios críticos de usuario donde aplica; mensajes `mensajes.py` / excepciones.
- **Frontend:** implementado en el repositorio `mpdw-frontend` (diálogos y conflictos de edición).

## Épica 5 — Catálogo de productos (2026-11-11) — **Status:** COMPLETED

| Historia | Estado | Evidencia |
|----------|--------|-----------|
| HU_MPDW_01_22 Crear producto | COMPLETED | `POST /api/v1/catalogo/productos/` |
| HU_MPDW_01_23 Listado y filtros | COMPLETED | `GET /api/v1/catalogo/productos/` |
| HU_MPDW_01_24 Editar producto | COMPLETED | `PATCH /api/v1/catalogo/productos/{id}/` |
| HU_MPDW_01_25 Cambiar estado | COMPLETED | `POST /api/v1/catalogo/productos/{id}/estado/` |
| HU_MPDW_01_26 Historial de precios | COMPLETED | `GET /api/v1/catalogo/productos/{id}/historial/` |
| HU_MPDW_01_27 / 28 Parámetros | COMPLETED | `/api/v1/catalogo/parametros/{tipo}/` |
| HU_MPDW_01_29 Importar | COMPLETED | `POST /api/v1/catalogo/productos/importar/` |
| HU_MPDW_01_30 Exportar | COMPLETED | `GET /api/v1/catalogo/productos/exportar/` |

Cierre parámetros (2026-11-12): `seed_catalogo_parametros`, accesos-panel con `categorias`/`marcas`/`tipos_producto`; docs `qa-epic-5.md`. Extras de sprint 2: `docs/user-stories-sprint2-extras.md`.

## Épica 6 — Inventario y kardex (2026-11-11) — **Status:** COMPLETED

| Historia | Estado | Evidencia |
|----------|--------|-----------|
| HU_MPDW_01_31 Existencias por sede | COMPLETED | `GET /api/v1/inventario/existencias/` |
| HU_MPDW_01_32 Entrada de mercancía | COMPLETED | `POST /api/v1/inventario/movimientos/entrada/` |
| HU_MPDW_01_33 Ajuste y merma | COMPLETED | `POST /api/v1/inventario/movimientos/ajuste/` |
| HU_MPDW_01_34 Traslado entre sedes | COMPLETED | `POST /api/v1/inventario/movimientos/traslado/` |
| HU_MPDW_01_35 Kardex | COMPLETED | `GET /api/v1/inventario/kardex/` |
| HU_MPDW_01_36 Alerta de stock bajo | COMPLETED | campo `alerta` en existencias |

Campos de demo (proveedor en texto y referencia) en `Movimientos_inventario`. QA: `docs/qa-epic-6.md`.

## Épica 7 — Directorio de clientes y Habeas Data (2026-11-12) — **v1.2.3** — **Status:** COMPLETED

| Historia | Estado | Evidencia |
|----------|--------|-----------|
| HU_MPDW_01_37 Crear cliente + consentimiento | COMPLETED | `POST /api/v1/clientes/`, e.164, Habeas Data, `fecha_consentimiento` |
| HU_MPDW_01_38 Directorio (búsqueda/filtros/WhatsApp) | COMPLETED | `GET /api/v1/clientes/`, wa.me e.164 sanitizado |
| HU_MPDW_01_39 Editar / desactivar cliente | COMPLETED | `PATCH /api/v1/clientes/{id}/`, concurrencia `version_fila` |
| HU_MPDW_01_40 Crear tipo de cliente | COMPLETED | `POST /api/v1/clientes/tipos/`, semilla «Común» |
| HU_MPDW_01_41 Editar tipo (proteger Común) | COMPLETED | `PATCH /api/v1/clientes/tipos/{id}/` |
| HU_MPDW_01_42 Detalle, historial y métricas | COMPLETED | `GET /api/v1/clientes/{id}/historial/` |

QA: `docs/qa-epic-7.md`. Extras demo: `docs/user-stories-sprint2-extras.md` (S2_13–S2_15).

## Épica 12 — Eventos y novedades (2026-11-12) — **v1.2.4** — **Status:** COMPLETED

| Historia | Estado | Evidencia |
|----------|--------|-----------|
| HU_MPDW_01_80 Crear evento | COMPLETED | `POST /api/v1/eventos/`, validaciones HU, sede global opcional |
| HU_MPDW_01_81 Editar / desactivar evento | COMPLETED | `PATCH /api/v1/eventos/{id}/`, auditoría, `version_fila` |

QA: `docs/qa-epic-12.md`. Público: `GET /api/v1/eventos/publicos/`. Extras: `docs/user-stories-sprint2-extras.md` (S2_16–S2_18).

## Épica 14 — Proveedores e inventario (2026-11-12) — **v1.2.5** — **Status:** COMPLETED

| Historia | Estado | Evidencia |
|----------|--------|-----------|
| HU_MPDW_01_84 Crear proveedor | COMPLETED | `POST /api/v1/proveedores/`, RBAC módulo 19 |
| HU_MPDW_01_85 Editar / activar proveedor | COMPLETED | `PATCH /api/v1/proveedores/{id}/`, concurrencia, auditoría |

Integración inventario: FK `id_proveedor` en `Movimientos_inventario` (`0004_epic14_proveedor_fk`). QA: `docs/qa-epic-14.md`. Extras: S2_19.
