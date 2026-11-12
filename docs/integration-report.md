# Integration report

## Epica 1
**Date:** 2026-11-04
**Status:** PARTIALLY_VERIFIED

### Contrato
El frontend consume los mismos caminos y los mismos textos que publica `GET /api/v1/auth/contrato` y `docs/openapi.yaml`.

| Criterio | Capa | Evidencia |
| --- | --- | --- |
| Login, bloqueo y mensajes | Backend | tests/unit/test_auth_service.py y test_epic1_auth.py, 152 passed |
| Formularios, boton deshabilitado, politica y mensajes | Frontend | src/features/auth/logic.test.ts, 3 passed; `pnpm run build` correcto |
| Cookie de refresh y rotacion | Contrato | OpenAPI regenerado y comparado por test_openapi_contract.py |
| Correo 2FA y recuperacion | Backend | plantillas y adaptadores cubiertos con dobles; el envio real depende del SMTP del entorno |
| Recorrido en navegador contra la API viva | Integracion | NOT_RUN en esta sesion |

### Motivo de NOT_RUN
No se levanto el par navegador-API contra la base de Supabase durante esta ejecucion. La logica de negocio y el contrato quedaron verificados con la suite unitaria y la compilacion del frontend. El siguiente paso operativo es `uv run python manage.py migrate` y `pnpm dev`, con el `.env` solo en la maquina local.

## Epica 2
**Date:** 2026-11-05
**Status:** VERIFIED (contrato y suites locales)

| Criterio | Capa | Evidencia |
| --- | --- | --- |
| CRUD administrativo y permiso `usuarios/T` | Backend | test_epic2_usuarios.py, test_epic2_usuarios_api.py |
| Mensajes literales CA 5–6 | Frontend | features/usuarios/messages.ts, logic.test.ts |
| Listado, filtros 300 ms debounce | Frontend | panel-usuarios-page.tsx |
| OpenAPI sin drift | Contrato | docs/openapi.yaml + test_openapi_contract |
| Calidad completa | Ambos | make calidad, npm exec pnpm run calidad |

## Epica 3
**Date:** 2026-11-05  
**Status:** VERIFIED (suites locales)

| Criterio | Capa | Evidencia |
| --- | --- | --- |
| CRUD roles/permisos y matriz | Backend | `/api/v1/roles-permisos/*`, test_epic3_* |
| Mensajes CA 5–6 literales | Backend | `mensajes.py`; toasts en frontend |
| Menu dinamico y acceso denegado | Frontend | `useAccesosPanel`, `PanelAccesoDenegadoPage` |
| Modulo Permisos (demo) | Frontend | `panel-permisos-page.tsx` |
| Filtros usuarios en una fila | Frontend | `panel-usuarios-page.tsx` |
| OpenAPI | Contrato | `docs/openapi.yaml` regenerado |

## Iteración 7 (2026-11-05)
**Status:** VERIFIED

| Criterio | Capa | Evidencia |
| --- | --- | --- |
| Sin acceso / Total en catálogo y evaluación | Backend | `permiso_eval.py`, `PermissionRepository` |
| Eliminar rol personalizado | API | `DELETE roles/{id}` + tests |
| Sesión tras F5 | Frontend | `session-storage`, bootstrap `providers` |
| Guards UI | Frontend | `AccesosProvider`, `logic.ts` |
| QA manual/automation | Docs | `docs/qa-epic-2.md`, `qa-epic-3.md` (frontend) |

## Cierre Sprint 1 — Épicas 13 y 18 (2026-11-06)
**Status:** VERIFIED (pipelines locales + contrato)

| Criterio | Capa | Evidencia |
| --- | --- | --- |
| Bitácora lectura + filtros | API | `GET /api/v1/auditoria/bitacora/`, `test_epic13_bitacora_service.py` |
| Opciones usuario filtro | API | `GET .../bitacora/usuarios/` |
| Sin secretos en JSON de auditoría | Dominio | `sanitize.py`, `test_epic13_auditoria_sanitize.py` |
| 409 conflicto versión | API | `ConflictoVersionError`, pruebas usuarios/sedes |
| Migraciones Supabase | Ops | `0002_ep13_auditoria_campos`, `0011_gerente_auditoria_consultar` |
| Cliente integrado | Frontend | `mpdw-frontend` rama homónima, `pnpm run calidad` |
| QA manual | Docs | `docs/qa-sprint1-closing.md` |
