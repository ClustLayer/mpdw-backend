# User stories

## HU_MPDW_01_01 — Iniciar sesion
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero autenticar mis credenciales (correo electronico y contraseña) en el sistema, para acceder unicamente a los modulos que mi rol autoriza y proteger la informacion del negocio.

### Criterios de aceptacion
1. La accion se realiza en la pantalla "Iniciar sesion".
2. Correo electronico obligatorio, maximo 255, formato valido. Mensaje: "El correo electronico ingresado no tiene un formato valido."
3. Contraseña obligatoria, oculta por defecto, con boton de visualizacion. Mensaje: "La contraseña es obligatoria."
4. El boton "Iniciar sesion" permanece inhabilitado mientras correo o contraseña esten vacios.
5. Si el usuario existe, esta activo, no tiene bloqueo vigente y la contraseña coincide con el hash, se crea la sesion, intentos_fallidos vuelve a 0, se actualiza ultimo_acceso y se redirige al inicio del rol. Si debe_cambiar_password, primero va a cambiar contraseña. Si el administrador tiene 2FA, va a la verificacion.
6. La contraseña no se guarda ni viaja en claro. Access token 15 minutos y refresh token 7 dias, ambos configurables. El refresh se guarda como hash. Los tokens no van en la URL ni en los logs.
7. Exito: "Bienvenido(a), {nombre}."
8. Credenciales, inactivo o contraseña incorrecta: "Credenciales no validas, por favor intente de nuevo." A los 5 intentos: "Acceso temporalmente bloqueado. Intente mas tarde o contacte al administrador."
9. Error no anticipado: "No fue posible iniciar sesion. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_02 — Cerrar sesion
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero cerrar mi sesion activa, para evitar que otra persona use mi cuenta en un equipo compartido.

### Criterios de aceptacion
1. La opcion "Cerrar sesion" esta en el menu de usuario de toda pantalla autenticada.
2. No captura datos y esta habilitada con sesion activa.
3. Revoca el refresh token (`fecha_revocacion`), invalida el access token, limpia el estado local y redirige a "Iniciar sesion".
4. Un token revocado no renueva la sesion (401). Tras el cierre, el boton Atras no deja ver rutas protegidas.
5. Exito: "Sesion cerrada correctamente."
6. Sesion ya expirada: "Su sesion ya habia expirado. Inicie sesion nuevamente."
7. Fallo de revocacion: "No fue posible cerrar la sesion en el servidor. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_03 — Recuperar contraseña
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero restablecer mi contraseña olvidada mediante un enlace temporal de un solo uso, para recuperar el acceso a mi cuenta sin depender del administrador.

### Criterios de aceptacion
1. Pantallas "Recuperar contraseña" y "Nueva contraseña".
2. Correo obligatorio. Boton "Enviar enlace" inhabilitado si esta vacio.
3. Nueva contraseña y confirmacion cumplen la politica de HU 04 y deben coincidir.
4. La respuesta al solicitar el enlace es siempre la misma, exista o no la cuenta.
5. El enlace dura 60 minutos, se guarda solo como hash, es de un solo uso y al usarse revoca las sesiones.
6. Exito de solicitud: "Si el correo esta registrado, recibira un enlace para restablecer su contraseña."
7. Exito de restablecimiento: "Su contraseña ha sido restablecida. Ya puede iniciar sesion."
8. Enlace invalido: "El enlace de recuperacion no es valido o ha expirado. Solicite uno nuevo."
9. Error no anticipado: "No fue posible completar la solicitud. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_04 — Cambiar contraseña
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero cambiar mi contraseña validando la contraseña actual, para mantener segura mi cuenta y cumplir el cambio obligatorio cuando se me asigne una contraseña temporal.

### Criterios de aceptacion
1. Pantalla "Cambiar contraseña", obligatoria si `debe_cambiar_password` es verdadero.
2. Contraseña actual, nueva y confirmacion. La nueva exige mayuscula, numero, caracter especial `!@#$%^&*` y longitud de 8 a 64, y debe ser distinta de la actual.
3. "Guardar contraseña" inhabilitado si falta un campo. "Cancelar" no aparece cuando el cambio es obligatorio.
4. Campos vacios: "Todos los campos obligatorios deben ser diligenciados."
5. Actual incorrecta: "La contraseña actual es incorrecta."
6. Politica: "La contraseña no cumple los requisitos minimos de seguridad."
7. Confirmacion distinta: "Las contraseñas no coinciden."
8. Se guarda solo el hash, `debe_cambiar_password` pasa a falso y la auditoria no guarda la contraseña.
9. Exito: "Su contraseña ha sido actualizada correctamente."
10. Error no anticipado: "No fue posible cambiar la contraseña. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_05 — Continuidad de sesion
**Historia de usuario:** Yo como administrador, gerente o empleado, quiero continuar mi sesion cuando el sistema me avise de su proxima expiracion por inactividad, para no perder el trabajo en curso.

### Criterios de aceptacion
1. Dialogo modal sobre cualquier pantalla autenticada.
2. Cuenta regresiva, boton "Continuar sesion" y boton "Cerrar sesion".
3. Inactividad por defecto de 60 minutos y aviso 5 minutos antes. Ambos vienen de la configuracion.
4. Continuar renueva los tokens con rotacion del refresh. Un refresh ya rotado revoca la familia.
5. Ante 401 el cliente intenta una sola renovacion.
6. Exito: "Su sesion continua activa."
7. Tiempo agotado: "Su sesion expiro por inactividad. Inicie sesion nuevamente."
8. Fallo tecnico: "No fue posible renovar la sesion. Inicie sesion nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED

## HU_MPDW_01_06 — Verificacion en dos pasos
**Historia de usuario:** Yo como administrador, quiero verificar mi identidad con un codigo de segundo paso al iniciar sesion, para proteger con una capa adicional la cuenta de mayores privilegios.

### Criterios de aceptacion
1. La pantalla aparece despues del login solo si el 2FA del administrador esta habilitado.
2. Codigo numerico de 6 digitos. Boton "Verificar" inhabilitado si esta vacio.
3. "Reenviar codigo" invalida el anterior.
4. El codigo se guarda solo como hash, dura 10 minutos y admite 3 intentos.
5. Exito: "Verificacion completada."
6. Codigo incorrecto: "El codigo ingresado no es valido."
7. Expirado o usado: "El codigo ha expirado. Solicite uno nuevo."
8. Error no anticipado: "No fue posible verificar el codigo. Intente nuevamente."

**Received:** 2026-11-04
**Status:** COMPLETED
