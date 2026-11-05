# Changelog

## 2026-11-05 — Correccion Mi perfil e integracion Epic 2

- Campos de perfil alineados con la demo: tipo de sangre, fecha de nacimiento, direccion y contacto de emergencia (migracion 0007).
- Pruebas de integracion Epic 2 autentican con JWT Bearer (corrige 403 por `auth_context` ausente).

## 2026-11-05 — Epica 2, administracion de usuarios y perfil

- Creacion de usuarios con rol, sede principal, contraseña inicial por correo y auditoria (HU 07).
- Listado administrativo con busqueda, filtros y paginacion (HU 08).
- Edicion de usuario con control de concurrencia optimista (HU 09).
- Cambio de estado activo, inactivo y bloqueado con revocacion de sesiones (HU 10).
- Generacion de contraseña temporal de un solo uso (HU 11).
- Mi perfil: nombre, apellido y telefono editables; documento, correo y rol de solo lectura (HU 12).

## 2026-11-04 — Epica 1, autenticacion y seguridad de sesion

- Inicio de sesion con mensajes literales, bloqueo configurable y auditoria sin secretos.
- Cierre de sesion con revocacion del refresh token.
- Recuperacion de contraseña por enlace de un solo uso y correo HTML.
- Cambio de contraseña con la politica de HU 04.
- Renovacion de sesion con rotacion del refresh token.
- Verificacion en dos pasos para el administrador, con codigo de un solo uso.
