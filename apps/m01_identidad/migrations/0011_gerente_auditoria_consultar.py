# Épica 13: Gerente puede consultar bitácora en solo lectura (CA 1)
from django.db import migrations


def add_permiso_lectura_auditoria_gerente(apps, schema_editor):
    Roles = apps.get_model("m01_identidad", "Roles")
    Permisos = apps.get_model("m01_identidad", "Permisos")
    Rol_permiso = apps.get_model("m01_identidad", "Rol_permiso")

    rol = Roles.objects.filter(nombre="Gerente").first()
    if not rol:
        return
    perm, _ = Permisos.objects.get_or_create(
        modulo="auditoria",
        accion="Consultar",
        defaults={
            "nombre": "auditoria · Consultar",
            "descripcion": "Lectura bitácora épica 13",
            "estado": True,
        },
    )
    Rol_permiso.objects.get_or_create(
        id_rol=rol, id_permiso=perm, defaults={"permitido": True}
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("m01_identidad", "0010_purge_legacy_permisos"),
    ]

    operations = [
        migrations.RunPython(add_permiso_lectura_auditoria_gerente, noop),
    ]
