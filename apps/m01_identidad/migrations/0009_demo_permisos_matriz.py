# Resincroniza permisos con la matriz de la demo (modos total/ver/propio/none → catálogo HU 16).
from django.db import migrations

PANEL_A_DOMINIO = {
    "resumen": "autenticacion_perfil",
    "usuarios": "usuarios",
    "permisos": "roles_permisos",
    "sedes": "sedes",
    "categorias": "catalogo_productos",
    "productos": "catalogo_productos",
    "inventario": "inventario_kardex",
    "clientes": "clientes",
    "proveedores": "proveedores",
    "ventas": "facturas",
    "pos": "pos",
    "domicilios": "domicilios",
    "facturacion": "facturacion_electronica",
    "caja": "cuentas_bancarias",
    "conceptos": "gastos_frecuentes",
    "cierre": "cierre_jornada",
    "eventos": "eventos",
    "promociones": "eventos",
    "auditoria": "auditoria",
    "analitica": "analitica",
}

DEMO_MODOS = {
    "Administrador": {
        "resumen": "total",
        "usuarios": "total",
        "permisos": "total",
        "sedes": "total",
        "categorias": "total",
        "productos": "total",
        "inventario": "total",
        "clientes": "total",
        "proveedores": "total",
        "ventas": "total",
        "pos": "total",
        "domicilios": "total",
        "facturacion": "total",
        "caja": "total",
        "conceptos": "total",
        "cierre": "total",
        "eventos": "total",
        "promociones": "total",
        "auditoria": "total",
        "analitica": "total",
    },
    "Gerente": {
        "resumen": "total",
        "usuarios": "none",
        "permisos": "none",
        "sedes": "none",
        "categorias": "none",
        "productos": "total",
        "inventario": "total",
        "clientes": "total",
        "proveedores": "none",
        "ventas": "total",
        "pos": "total",
        "domicilios": "total",
        "facturacion": "total",
        "caja": "total",
        "conceptos": "total",
        "cierre": "total",
        "eventos": "total",
        "promociones": "total",
        "auditoria": "none",
        "analitica": "total",
    },
    "Empleado": {
        "resumen": "propio",
        "usuarios": "none",
        "permisos": "none",
        "sedes": "none",
        "categorias": "none",
        "productos": "ver",
        "inventario": "ver",
        "clientes": "total",
        "proveedores": "none",
        "ventas": "propio",
        "pos": "total",
        "domicilios": "total",
        "facturacion": "none",
        "caja": "none",
        "conceptos": "none",
        "cierre": "none",
        "eventos": "none",
        "promociones": "none",
        "auditoria": "none",
        "analitica": "none",
    },
}

MODO_A_ACCION = {
    "total": "Total",
    "ver": "Consultar",
    "propio": "Consultar",
    "none": "Sin acceso",
}


def resync_demo_permisos(apps, schema_editor):
    Roles = apps.get_model("m01_identidad", "Roles")
    Permisos = apps.get_model("m01_identidad", "Permisos")
    Rol_permiso = apps.get_model("m01_identidad", "Rol_permiso")
    Usuario_permiso = apps.get_model("m01_identidad", "Usuario_permiso")

    Usuario_permiso.objects.all().delete()
    Rol_permiso.objects.all().delete()
    Permisos.objects.all().delete()

    roles = {r.nombre: r for r in Roles.objects.filter(nombre__in=DEMO_MODOS.keys())}
    for rol_nombre, modos in DEMO_MODOS.items():
        rol = roles.get(rol_nombre)
        if not rol:
            continue
        for panel, modo in modos.items():
            dominio = PANEL_A_DOMINIO.get(panel)
            if not dominio:
                continue
            accion = MODO_A_ACCION[modo]
            perm, _ = Permisos.objects.get_or_create(
                modulo=dominio,
                accion=accion,
                defaults={
                    "nombre": f"{panel} · {accion}",
                    "descripcion": "Semilla demo épica 4",
                    "estado": True,
                },
            )
            Rol_permiso.objects.get_or_create(
                id_rol=rol, id_permiso=perm, defaults={"permitido": True}
            )


class Migration(migrations.Migration):
    dependencies = [
        ("m01_identidad", "0008_epic3_roles_permisos"),
    ]

    operations = [
        migrations.RunPython(resync_demo_permisos, migrations.RunPython.noop),
    ]
