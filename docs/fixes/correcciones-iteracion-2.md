# Iteración 2 — Seguridad, concurrencia y CI

## Backend (ítems 5–18)

- Serialización de emisión 2FA con `crear_serializado()` bajo `select_for_update()` del usuario.
- Consumo atómico de token de recuperación con `consumir_token_atomico()` y conteo de filas afectadas.
- Verificación MFA serializada con `intentar_consumir_codigo()` y bloqueo de fila del código vigente.
- Cambio de contraseña y recuperación envueltos en `transaction.atomic()`; auditoría dentro del mismo bloque en cambio autenticado.
- Campo `credential_version` en `Usuarios` y claim `cv` en JWT; revocación de access tokens tras cambio de clave.
- SMTP `starttls(context=ssl.create_default_context())`.
- Validación de Origin/Referer en refresh y logout; cookie refresh no se borra en respuestas 500 de logout.
- Emisión de código 2FA tras cambio de clave obligatorio con `desafio_token` en la respuesta.
- Reenvío 2FA renueva vigencia del código al tiempo restante del desafío y devuelve nuevo `desafio_token`.
- `Reenviar2FARequestSerializer` solo exige `desafio_token`; OpenAPI regenerado.
- Escáner de secretos excluye archivos `*.example`.
- Pruebas de concurrencia en `tests/concurrency/test_auth_concurrency.py`.

## Frontend

- Ver `mpdw-frontend/docs/correcciones-iteracion-2.md` (restauración visual demo).
