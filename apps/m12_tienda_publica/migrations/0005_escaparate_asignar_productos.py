"""Asigna productos activos a las vitrinas demo del inicio (corrige carruseles vacíos)."""

from django.db import migrations


def asignar_productos(apps, schema_editor):
    Escaparate = apps.get_model("m12_tienda_publica", "Escaparate_seccion")
    EscaparateProducto = apps.get_model("m12_tienda_publica", "Escaparate_producto")
    Productos = apps.get_model("m03_catalogo", "Productos")

    activos = list(Productos.objects.filter(estado=True).order_by("id_producto").values_list("id_producto", flat=True)[:40])
    if not activos:
        return

    # Reparto por bloques para que cada sección tenga variedad
    chunks = [
        activos[0:8] or activos[:4],
        activos[8:16] or activos[4:12] or activos[:4],
        activos[16:24] or activos[8:16] or activos[:4],
        activos[24:32] or activos[12:20] or activos[:4],
    ]
    for idx, sec in enumerate(Escaparate.objects.filter(estado=True).order_by("orden", "id_escaparate")):
        if EscaparateProducto.objects.filter(id_escaparate=sec).exists():
            continue
        ids = chunks[idx % len(chunks)]
        for orden, pid in enumerate(ids):
            EscaparateProducto.objects.get_or_create(
                id_escaparate=sec,
                id_producto_id=pid,
                defaults={"orden": orden},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("m12_tienda_publica", "0004_escaparate_demo_inicio"),
        ("m03_catalogo", "0006_vinilos_colores_demo"),
    ]

    operations = [
        migrations.RunPython(asignar_productos, migrations.RunPython.noop),
    ]