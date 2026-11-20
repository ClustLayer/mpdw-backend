# Correcciones iteración 4 (HU MPDW 01)

## Base de datos y usuarios

- Migraciones aplicadas sobre Supabase (conexión pooler documentada en iteraciones previas).
- Comando `seed_epic1_demo_users` ampliado con administrador opcional vía `DEMO_OWNER_*` y sincronización controlada con `DEMO_SYNC_PASSWORDS`.

## Correo

- Comando `enviar_correo_prueba` para validar SMTP/Brevo con plantilla de recuperación (destino en `CORREO_PRUEBA_DESTINO`).
- Si el relay responde `SMTPAuthenticationError`, renueve la clave SMTP en Brevo o configure `SENDGRID_API_KEY` y deje `SMTP_HOST` vacío para usar SendGrid.

## Operación local

- Variables de ejemplo documentadas en `.env.example` sin secretos versionados.
