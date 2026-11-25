"""Semilla idempotente métodos de pago y tipos de venta (Épica 8)."""

from django.db import migrations


def seed(apps, schema_editor):
    Metodos = apps.get_model("m06_ventas", "Metodos_pago")
    Tipos = apps.get_model("m06_ventas", "Tipos_venta")
    for nombre in ("Efectivo", "Transferencia"):
        Metodos.objects.get_or_create(nombre=nombre, defaults={"estado": True})
    for nombre in ("Mostrador", "Mayorista", "Corporativo"):
        Tipos.objects.get_or_create(nombre=nombre, defaults={"estado": True})


class Migration(migrations.Migration):
    dependencies = [("m06_ventas", "0003_epic8_pos_facturacion")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]