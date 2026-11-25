# Épica 21: permisos demo para módulo promociones (Gerente/Admin).
from django.db import migrations

PANEL_DOMINIO = {"promociones": "promociones"}


def permisos_promociones(apps, schema_editor):
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
        modo = modos.get("promociones", "none")
        if modo == "none":
            accion = "Sin acceso"
        else:
            accion = demo.MODO_A_ACCION[modo]
        dominio = PANEL_DOMINIO["promociones"]
        perm, _ = Permisos.objects.get_or_create(
            modulo=dominio,
            accion=accion,
            defaults={
                "nombre": f"promociones · {accion}",
                "descripcion": "Semilla épica 21 promociones",
                "estado": True,
            },
        )
        Rol_permiso.objects.get_or_create(id_rol=rol, id_permiso=perm, defaults={"permitido": True})


class Migration(migrations.Migration):
    dependencies = [
        ("m01_identidad", "0013_epic11_categorias_caja_demo"),
    ]

    operations = [
        migrations.RunPython(permisos_promociones, migrations.RunPython.noop),
    ]