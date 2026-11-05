# Despliegue del backend en Render

1. Cree un Web Service desde este repositorio, rama `epica-1-autenticacion` o la que vaya a promover.
2. Runtime: Docker. El `Dockerfile` ya arranca Gunicorn en `$PORT`.
3. Defina en el panel de Render, no en el repositorio: `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`, `DATABASE_URL`, `DATABASE_MIGRATE_URL`, `SENDGRID_API_KEY` o `SMTP_HOST`/`SMTP_USER`/`SMTP_PASS`, `FRONTEND_URL` y `CORS_ALLOWED_ORIGINS` con el dominio de Vercel.
4. `DJANGO_SETTINGS_MODULE=config.settings.production`.
5. Comando de release: `python manage.py migrate`.
6. Compruebe `GET /api/v1/health/` y un `POST /api/v1/auth/login` por HTTPS. El refresh viaja en cookie `HttpOnly` con `SameSite=None` y `Secure`.

No copie el `.env` local al panel ni al repositorio.
