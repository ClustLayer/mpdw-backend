# Correcciones iteración 5 (HU MPDW 01)

## Supabase y usuarios

- Migraciones aplicadas en la base en nube; semilla de usuarios demo y administrador opcional vía `seed_epic1_demo_users`.

## Recuperación y correo

- El envío SMTP fallido en recuperación ya no aborta la solicitud HTTP (se registra en log y se responde el mensaje uniforme).
- Comando `enviar_correo_prueba` validado contra Brevo tras ajuste de restricciones de red.
