from django.db import migrations


def vincular_vinilos(apps, schema_editor):
    Productos = apps.get_model("m03_catalogo", "Productos")
    Colores = apps.get_model("m03_catalogo", "Colores_catalogo")
    Productos_colores = apps.get_model("m03_catalogo", "Productos_colores")
    azul = Colores.objects.filter(nombre="Azul").first()
    rojo = Colores.objects.filter(nombre="Rojo").first()
    if not azul or not rojo:
        return
    for p in Productos.objects.filter(estado=True, nombre__icontains="vinilo")[:20]:
        for color in (azul, rojo):
            Productos_colores.objects.get_or_create(id_producto_id=p.id_producto, id_color_id=color.id_color)


class Migration(migrations.Migration):
    dependencies = [("m03_catalogo", "0005_colores_producto")]

    operations = [migrations.RunPython(vincular_vinilos, migrations.RunPython.noop)]