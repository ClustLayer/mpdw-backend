# Elimina permisos legacy (L, O, T…) y reaplica semilla demo.
import importlib

from django.db import migrations

ACCIONES_VIGENTES = (
    "Crear",
    "Consultar",
    "Editar",
    "Cambiar estado",
    "Anular",
    "Exportar",
    "Sin acceso",
    "Total",
)


def purge_y_resync(apps, schema_editor):
    Permisos = apps.get_model("m01_identidad", "Permisos")
    Rol_permiso = apps.get_model("m01_identidad", "Rol_permiso")
    Usuario_permiso = apps.get_model("m01_identidad", "Usuario_permiso")
    legacy = Permisos.objects.exclude(accion__in=ACCIONES_VIGENTES)
    legacy_ids = list(legacy.values_list("pk", flat=True))
    if legacy_ids:
        Rol_permiso.objects.filter(id_permiso_id__in=legacy_ids).delete()
        Usuario_permiso.objects.filter(id_permiso_id__in=legacy_ids).delete()
        legacy.delete()
    mod = importlib.import_module("apps.m01_identidad.migrations.0009_demo_permisos_matriz")
    mod.resync_demo_permisos(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        ("m01_identidad", "0009_demo_permisos_matriz"),
    ]

    operations = [
        migrations.RunPython(purge_y_resync, migrations.RunPython.noop),
    ]
