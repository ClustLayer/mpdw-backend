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
