# ==============================================================================
# Semillas Versionadas de Roles Base, Permisos y Matriz Anexo A - MPDW
# SAD Ref: M01, §4.1, §8.1, §18 Anexo A, BR-10, RI-21
# ==============================================================================
from django.db import migrations

from contratos.catalogos import MATRIZ_ANEXO_A


def sembrar_roles_y_permisos(apps, schema_editor):
    Roles = apps.get_model("m01_identidad", "Roles")
    Permisos = apps.get_model("m01_identidad", "Permisos")
    Rol_permiso = apps.get_model("m01_identidad", "Rol_permiso")

    # 1. Roles Base del Sistema (SAD §4.1, BR-10, RI-21)
    # Estrictamente los tres roles base protegidos de la arquitectura
    admin_rol, _ = Roles.objects.get_or_create(
        nombre="Administrador",
        defaults={"descripcion": "Acceso total al backoffice y configuracion global", "es_rol_base": True, "estado": True},
    )
    gerente_rol, _ = Roles.objects.get_or_create(
        nombre="Gerente",
        defaults={"descripcion": "Supervision de ventas, caja, inventario y personal de sede", "es_rol_base": True, "estado": True},
    )
    empleado_rol, _ = Roles.objects.get_or_create(
        nombre="Empleado",
        defaults={"descripcion": "Operacion POS, atencion en mostrador, ventas y caja", "es_rol_base": True, "estado": True},
    )

    roles_map = {
        "Empleado": empleado_rol,
        "Gerente": gerente_rol,
        "Administrador": admin_rol,
    }

    # 2. Semilla generada estrictamente desde la fuente unica MATRIZ_ANEXO_A (SAD §18 Anexo A)
    # 19 secciones × 3 roles = 57 celdas contractuales
    # 'T' = Total/CRUD, 'L' = Lectura, 'O' = Operacion transaccional, '—' = Sin acceso
    for id_sec, modulo, nombre_sec, emp_acc, ger_acc, adm_acc in MATRIZ_ANEXO_A:
        celdas = [
            ("Empleado", emp_acc),
            ("Gerente", ger_acc),
            ("Administrador", adm_acc),
        ]
        for rol_nombre, accion in celdas:
            if accion != "—":
                perm, _ = Permisos.objects.get_or_create(
                    modulo=modulo,
                    accion=accion,
                    defaults={"descripcion": f"{id_sec}. {nombre_sec} ({accion})"},
                )
                rol = roles_map[rol_nombre]
                Rol_permiso.objects.get_or_create(id_rol=rol, id_permiso=perm)


def revertir_roles_y_permisos(apps, schema_editor):
    Rol_permiso = apps.get_model("m01_identidad", "Rol_permiso")
    Permisos = apps.get_model("m01_identidad", "Permisos")
    Roles = apps.get_model("m01_identidad", "Roles")

    Rol_permiso.objects.all().delete()
    Permisos.objects.all().delete()
    Roles.objects.filter(nombre__in=["Administrador", "Gerente", "Empleado"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("m01_identidad", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sembrar_roles_y_permisos, reverse_code=revertir_roles_y_permisos),
    ]
