# Implementation report

## Epica 1 — Autenticacion y seguridad de sesion
**Status:** COMPLETED
**Date:** 2026-11-04

### Analysis (orchestrator)
- project_mode backend: EXTEND_EXISTING. El modulo `m01_identidad` ya emitia JWT y refresh opaco.
- project_mode frontend: MOCKUP_PRODUCTIONIZATION. La demo `MundoPinturasDiana-Demo` queda intacta y el portal de produccion vive en `mpdw-frontend`.
- Classification: FULL_STACK
- Complexity: COMPLEX (92). Autenticacion, sesion, datos personales, migracion y correo.
- Routing: backend, frontend e integrador.

### Decisiones
- Los mensajes de las historias reemplazan los textos previos del servicio. Las pruebas unitarias quedaron alineadas.
- La columna fisica del refresh sigue llamandose `fecha_expiracion_absoluta`. El dominio expone `fecha_expiracion` para no reescribir el esquema que ya usa el resto del backend.
- El hash de contraseña sigue en la columna `password` de Django (Argon2id). No se duplica.
- Si el administrador debe cambiar la contraseña y ademas tiene 2FA, primero cambia la contraseña y despues verifica el codigo. Mientras tanto el JWT no abre el resto de la API.
- El enlace de recuperacion viaja en el fragmento `#rt=` para que el token no quede en los logs del servidor web. En base de datos solo se guarda el hash.
- El correo sale por SendGrid si hay API key y, si no, por el SMTP del entorno. El `.env` local no se versiona.

### Backend
- Migracion `0004_epic1_autenticacion`.
- Servicios, vistas, puerto de correo, adaptador SMTP y plantillas HTML.
- Pruebas: `tests/unit/test_auth_service.py`, `tests/unit/test_epic1_auth.py` y el contrato OpenAPI.

### Evidencia
- `uv run pytest tests/unit -m unit`: 152 passed.
- `uv run mypy apps/m01_identidad apps/m13_plataforma/adapters`: sin errores.
- `uv run ruff check` sobre los archivos tocados: sin errores.
- `uv run python scripts/scan_secrets.py`: sin hallazgos en archivos versionados.
- `uv run python scripts/complejidad.py`: todas las funciones de `services.py` bajo 20.
- Cobertura de la suite unitaria: 94.12% (umbral 90%).

### No verificado en esta corrida
- La suite de integracion con PostgreSQL no se ejecuto en esta maquina porque no habia un servicio local levantado. El pipeline de CI si la ejecuta.
