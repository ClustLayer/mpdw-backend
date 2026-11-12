# Configuracion

La arquitectura por modulos no cambia: `apps/m01_identidad` atiende la autenticacion,
`apps/m10_auditoria` registra los eventos y `apps/m13_plataforma` envia el correo.

Variables nuevas, siempre por entorno y nunca en el repositorio:

- `ACCESS_TOKEN_LIFETIME_MINUTES` (15), `REFRESH_TOKEN_LIFETIME_DAYS` (7)
- `INACTIVITY_TIMEOUT_MINUTES` (60), `SESSION_WARNING_MINUTES` (5)
- `MAX_INTENTOS_FALLIDOS` (5), `BLOQUEO_MINUTOS` (15)
- `RECUPERACION_MINUTOS` (60), `CODIGO_2FA_MINUTOS` (10), `MAX_INTENTOS_2FA` (3)
- `FRONTEND_URL`
- `SENDGRID_API_KEY` o, si queda vacia, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`

El archivo local `.env` esta ignorado. La plantilla es `.env.example`.
