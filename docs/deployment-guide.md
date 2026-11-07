# Despliegue del backend en Render

1. Cree un Web Service desde este repositorio, rama a promover (p. ej. `develop` / release).
2. Runtime: Docker. El `Dockerfile` ya arranca Gunicorn en `$PORT`.
3. Defina en el panel de Render, no en el repositorio:
   - `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`
   - `DATABASE_URL` del **Session/Transaction pooler** de Supabase con usuario
     `postgres.<PROJECT_REF>` (no use solo `postgres` en el pooler)
   - `DATABASE_MIGRATE_URL` (conexión de sesión, puerto 5432 del pooler o directa)
   - `SENDGRID_API_KEY` o `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS`
   - `FRONTEND_URL` y `CORS_ALLOWED_ORIGINS` con el dominio de Vercel
4. `DJANGO_SETTINGS_MODULE=config.settings.production` (activa SSL y opciones de pooler).
5. Comando de release (orden obligatorio):

```bash
python manage.py migrate --noinput
python manage.py createcachetable
```

   La tabla `django_cache` es requerida por el throttle DRF (ADR-010). Sin ella,
   el throttle degrada sin 500, pero se pierde el límite de tasa.
6. Compruebe `GET /api/v1/health/live`, `GET /api/v1/health/ready` y un
   `POST /api/v1/auth/login` por HTTPS. El refresh viaja en cookie `HttpOnly`
   con `SameSite=None` y `Secure`.

## Supabase / pooler

- `DISABLE_SERVER_SIDE_CURSORS=True` y `prepare_threshold=None` están fijados en settings.
- En producción se fuerza `sslmode=require`.
- Si el host es `*.pooler.supabase.com` y el usuario es solo `postgres`, la API
  registrará una advertencia: use `postgres.<PROJECT_REF>`.

No copie el `.env` local al panel ni al repositorio.
