"""Mensajes literales de la epica 1. No reformular."""

MSG_EMAIL_INVALIDO = "El correo electrónico ingresado no tiene un formato válido."
MSG_PASSWORD_VACIA = "La contraseña es obligatoria."
MSG_CREDENCIALES = "Credenciales no válidas, por favor intente de nuevo."
MSG_BLOQUEADO = "Acceso temporalmente bloqueado. Intente más tarde o contacte al administrador."
MSG_ERROR_LOGIN = "No fue posible iniciar sesión. Intente nuevamente."
MSG_BIENVENIDA = "Bienvenido(a), {nombre}."

MSG_LOGOUT_OK = "Sesión cerrada correctamente."
MSG_SESION_EXPIRADA = "Su sesión ya había expirado. Inicie sesión nuevamente."
MSG_LOGOUT_FALLO = "No fue posible cerrar la sesión en el servidor. Intente nuevamente."

MSG_RECUPERACION_OK = (
    "Si el correo está registrado, recibirá un enlace para restablecer su contraseña."
)
MSG_RESET_OK = "Su contraseña ha sido restablecida. Ya puede iniciar sesión."
MSG_RESET_INVALIDO = "El enlace de recuperación no es válido o ha expirado. Solicite uno nuevo."
MSG_ERROR_SOLICITUD = "No fue posible completar la solicitud. Intente nuevamente."

MSG_PASSWORD_POLITICA = "La contraseña no cumple los requisitos mínimos de seguridad."
MSG_PASSWORD_DISTINTA = "Las contraseñas no coinciden."
MSG_PASSWORD_ACTUAL = "La contraseña actual es incorrecta."
MSG_CAMPOS_OBLIGATORIOS = "Todos los campos obligatorios deben ser diligenciados."
MSG_CAMBIO_OK = "Su contraseña ha sido actualizada correctamente."
MSG_CAMBIO_ERROR = "No fue posible cambiar la contraseña. Intente nuevamente."

MSG_SESION_CONTINUA = "Su sesión continúa activa."
MSG_INACTIVIDAD = "Su sesión expiró por inactividad. Inicie sesión nuevamente."
MSG_RENOVAR_ERROR = "No fue posible renovar la sesión. Inicie sesión nuevamente."

MSG_2FA_OK = "Verificación completada."
MSG_2FA_INVALIDO = "El código ingresado no es válido."
MSG_2FA_EXPIRADO = "El código ha expirado. Solicite uno nuevo."
MSG_2FA_ERROR = "No fue posible verificar el código. Intente nuevamente."
MSG_2FA_REENVIADO = "Se generó un nuevo código. El anterior quedó invalidado."

MSG_DOCUMENTO_DUPLICADO = "Ya existe un usuario registrado con este documento."
MSG_DOCUMENTO_INVALIDO = "El documento de identidad ingresado no tiene un formato válido."
MSG_EMAIL_DUPLICADO = "Ya existe una cuenta registrada con este correo electrónico."
MSG_TELEFONO_INVALIDO = "El teléfono ingresado no tiene un formato válido."
MSG_TIPO_SANGRE_INVALIDO = "El tipo de sangre seleccionado no es válido."
MSG_FECHA_NACIMIENTO_INVALIDA = "La fecha de nacimiento ingresada no es válida."
MSG_TELEFONO_EMERGENCIA_INVALIDO = "El teléfono de emergencia ingresado no tiene un formato válido."
MSG_USUARIO_CREADO = "Usuario creado correctamente."
MSG_USUARIO_CREAR_ERROR = "No fue posible crear el usuario. Intente nuevamente."
MSG_EMAIL_ENTREGA_FALLIDA = (
    "No fue posible enviar el correo con la contraseña inicial. "
    "Genere una contraseña temporal o intente nuevamente."
)
MSG_USUARIO_NO_ENCONTRADO = "Usuario no encontrado."
MSG_USUARIO_ACTUALIZADO = "Usuario actualizado correctamente."
MSG_USUARIO_ACTUALIZAR_ERROR = "No fue posible actualizar el usuario. Intente nuevamente."
MSG_ESTADO_ACTUALIZADO = "El estado del usuario se actualizó correctamente."
MSG_ESTADO_ERROR = "No fue posible cambiar el estado del usuario. Intente nuevamente."
MSG_LISTADO_USUARIOS = "Mostrando {n} de {total} usuarios."
MSG_LISTADO_VACIO = "No se encontraron usuarios con los criterios indicados."
MSG_LISTADO_ERROR = "No fue posible cargar los usuarios. Intente nuevamente."
MSG_CONTRASENA_TEMP_OK = (
    "Contraseña temporal generada. El usuario deberá cambiarla en su siguiente acceso."
)
MSG_CONTRASENA_TEMP_ERROR = "No fue posible generar la contraseña temporal. Intente nuevamente."
MSG_CONTRASENA_TEMP_PROPIA = "No puede generar una contraseña temporal para su propia cuenta."
MSG_PERFIL_ACTUALIZADO = "Su perfil ha sido actualizado correctamente."
MSG_PERFIL_ERROR = "No fue posible actualizar su perfil. Intente nuevamente."
MSG_ROL_PROPIO = "No puede modificar su propio rol."
MSG_CONCURRENCIA = "El registro cambió mientras confirmaba. Actualice e intente nuevamente."
MSG_SEDE_OBLIGATORIA = "Debe asignar al menos una sede activa y marcar una como principal."
MSG_ROL_INACTIVO = "El rol seleccionado no está disponible."

MSG_ROL_NOMBRE_OBLIGATORIO = "El nombre del rol es obligatorio."
MSG_ROL_NOMBRE_DUPLICADO = "Ya existe un rol registrado con este nombre."
MSG_ROL_CREADO = "Rol creado correctamente."
MSG_ROL_CREAR_ERROR = "No fue posible crear el rol. Intente nuevamente."
MSG_ROL_ACTUALIZADO = "Rol actualizado correctamente."
MSG_ROL_ACTUALIZAR_ERROR = "No fue posible actualizar el rol. Intente nuevamente."
MSG_ROL_BASE_PROTEGIDO = "Los roles base no pueden ser modificados ni eliminados."
MSG_ROL_ELIMINADO = "Rol eliminado correctamente."
MSG_ROL_ELIMINAR_ERROR = "No fue posible eliminar el rol. Intente nuevamente."
MSG_ROL_ELIMINAR_ASIGNADO = "No es posible eliminar el rol porque tiene usuarios asignados."
MSG_ROL_INACTIVAR_USUARIOS = (
    "No es posible inactivar el rol porque tiene usuarios activos asignados. "
    "Reasigne los usuarios a otro rol antes de desactivarlo."
)
MSG_LISTADO_ROLES = "Mostrando {n} de {total} roles."
MSG_LISTADO_ROLES_VACIO = "No se encontraron roles con los criterios indicados."

MSG_PERMISO_CAMPOS = "Todos los campos obligatorios deben ser diligenciados."
MSG_PERMISO_DUPLICADO = "Ya existe un permiso para este módulo y esta acción."
MSG_PERMISO_CREADO = "Permiso creado correctamente."
MSG_PERMISO_CREAR_ERROR = "No fue posible crear el permiso. Intente nuevamente."
MSG_PERMISO_ACTUALIZADO = "Permiso actualizado correctamente."
MSG_PERMISO_ACTUALIZAR_ERROR = "No fue posible actualizar el permiso. Intente nuevamente."
MSG_PERMISO_INACTIVADO = (
    "El permiso se ha inactivado correctamente y sus accesos han sido revocados."
)
MSG_LISTADO_PERMISOS = "Mostrando {n} de {total} permisos."

MSG_MATRIZ_DESTINO = "Seleccione un rol o un usuario."
MSG_MATRIZ_GUARDADA = "Permisos actualizados correctamente. Los cambios aplican de inmediato."
MSG_MATRIZ_ERROR = "No fue posible guardar los permisos. Intente nuevamente."

MSG_PERMISO_DENEGADO = "No tiene permisos para realizar esta operación."
MSG_PERMISO_VERIFICAR_ERROR = "No fue posible verificar sus permisos. Intente nuevamente."
MSG_ACCESO_DENEGADO_RUTA = "No tiene permisos para acceder a este recurso."
