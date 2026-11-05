# Iteración 1 — Correcciones dirigidas (épica autenticación)

Registro declarativo de ajustes aplicados en esta iteración FIX full-stack.

## Backend

- Se corrigió el orden de imports en `scripts/complejidad.py` y `scripts/scan_secrets.py` para cumplir Ruff (I001).
- Se cargó `.env.test` cuando `DJANGO_SETTINGS_MODULE` apunta a `config.settings.testing`, evitando mezclar credenciales de desarrollo en pytest local.
- Las pruebas locales usan SQLite en memoria; CI activa PostgreSQL efímero con `MPDW_TEST_USE_POSTGRES=true`.
- Se añadió `.env.test.example` como plantilla de entorno de pruebas sin conexión a Supabase en nube.
- Se añadió el comando `seed_epic1_demo_users` para crear usuarios por rol mediante variables de entorno (sin secretos en el repositorio).
- Se amplió `.env.example` con variables de demostración y notas de desarrollo en nube vs Docker local.

## Conectividad Supabase

- El host directo `db.<ref>.supabase.co` puede resolver solo IPv6; si `getaddrinfo failed` o `Network is unreachable`, configure `DATABASE_URL` (y `DATABASE_MIGRATE_URL`) con el **Session pooler IPv4** del panel de Supabase.
- Script de diagnóstico: `uv run python scripts/verify_db_connection.py`.
- Tras conectar: `uv run python manage.py migrate` y `uv run python manage.py seed_epic1_demo_users` con contraseñas solo en variables de entorno.

## Pendiente de verificación manual

- Flujo completo login / refresh / logout con frontend en `http://localhost:5173` y API en `http://localhost:8000`.
- Envío real de correo (recuperación y 2FA) según proveedor SMTP configurado en `.env` local.
