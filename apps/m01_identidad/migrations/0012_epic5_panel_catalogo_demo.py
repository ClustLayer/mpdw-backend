# Épica 5: filas de matriz Marcas y Tipos (dominio catalogo_productos) — alinea semilla demo.
from django.db import migrations

PANEL_EXTRA = {
    "marcas": "catalogo_productos",
    "tipos_producto": "catalogo_productos",
}


def _modo_panel(panel: str, modos: dict[str, str]) -> str:
    if panel in modos:
        return modos[panel]
    if panel in PANEL_EXTRA:
        return modos.get("productos") or modos.get("categorias") or "none"
    return "none"


def ampliar_demo_catalogo(apps, schema_editor):
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
        for panel in PANEL_EXTRA:
            modo = _modo_panel(panel, modos)
            dominio = PANEL_EXTRA[panel]
            accion = demo.MODO_A_ACCION[modo]
            perm, _ = Permisos.objects.get_or_create(
                modulo=dominio,
                accion=accion,
                defaults={
                    "nombre": f"{panel} · {accion}",
                    "descripcion": "Semilla épica 5 panel catálogo",
                    "estado": True,
                },
            )
            Rol_permiso.objects.get_or_create(id_rol=rol, id_permiso=perm, defaults={"permitido": True})


class Migration(migrations.Migration):
    dependencies = [
        ("m01_identidad", "0011_gerente_auditoria_consultar"),
    ]

    operations = [
        migrations.RunPython(ampliar_demo_catalogo, migrations.RunPython.noop),
    ]
