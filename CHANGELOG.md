# Changelog

Versionado del producto (major.sprint.epica): **1.1.5** = producto 1, sprint 1, cierre con épicas 13 y 18 en esta entrega. Las épicas 1–4 quedan reflejadas en **1.1.1**–**1.1.4** respectivamente en el historial de cambios por entrega.

## 2026-11-06 — v1.1.5 Cierre Sprint 1 (Épica 13 Auditoría, Épica 18 transversal)

- Bitácora de auditoría (HU 82): `GET /api/v1/auditoria/bitacora/` con filtros combinables, paginación validada y mensajes CA; `GET .../bitacora/usuarios/` para el combo con búsqueda.
- Sanitización de secretos en payload de auditoría; ampliación de modelo/migración (`accion` 50, `ip` 45); permiso de consulta extendido a gerente según CA 1.
- Concurrencia optimista unificada (`ConflictoVersionError` → HTTP 409); motivo obligatorio en operaciones críticas de usuario donde aplica.
- Cobertura unitaria ≥90% y contrato OpenAPI regenerado.

## 2026-11-05 — Deuda tecnica Copilot (Epic 2)

- Admin usuarios: unicidad de email bajo bloqueo, revocacion JWT al desactivar/bloquear, N+1 en sede principal, 404 uniforme y entrega de correo verificada.
- OpenAPI: respuestas de contraseña temporal, catalogo de roles y PATCH de perfil parcial.
- Plantilla de correo con escape HTML.

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
