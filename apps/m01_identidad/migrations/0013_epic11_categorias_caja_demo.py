# Épica 11: permisos demo para categorías de movimientos de caja.
from django.db import migrations

PANEL_DOMINIO = {"categorias_caja": "categorias_movimientos"}


def _modo_conceptos(modos: dict[str, str]) -> str:
    return modos.get("conceptos") or modos.get("cierre") or "none"


def permisos_categorias_caja(apps, schema_editor):
    import importlib

    demo = importlib.import_module("apps.m01_identidad.migrations.0009_demo_permisos_matriz")
    Roles = apps.get_model("m01_identidad", "Roles")
    Permisos = apps.get_model("m01_identidad", "Permisos")
    Rol_permiso = apps.get_model("m01_identidad", "Rol_permiso")

    roles = {r.nombre: r for r in Roles.objects.filter(nombre__in=demo.DEMO_MODOS.keys())}
    for rol_nombre, modos in demo.DEMO_MODOS.items():
        rol = roles.get(rol_nombre)
        if not rol:
            continue
        modo = _modo_conceptos(modos)
        dominio = PANEL_DOMINIO["categorias_caja"]
        accion = demo.MODO_A_ACCION[modo]
        perm, _ = Permisos.objects.get_or_create(
            modulo=dominio,
            accion=accion,
            defaults={
                "nombre": f"categorias_caja · {accion}",
                "descripcion": "Semilla épica 11 categorías de caja",
                "estado": True,
            },
        )
        Rol_permiso.objects.get_or_create(id_rol=rol, id_permiso=perm, defaults={"permitido": True})


class Migration(migrations.Migration):
    dependencies = [
        ("m01_identidad", "0012_epic5_panel_catalogo_demo"),
    ]

    operations = [
        migrations.RunPython(permisos_categorias_caja, migrations.RunPython.noop),
    ]