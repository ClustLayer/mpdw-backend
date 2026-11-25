"""Quita cantidad_anterior y cantidad_nueva del kardex (solo cantidad del movimiento)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("m04_inventario", "0004_epic14_proveedor_fk"),
    ]

    operations = [
        migrations.RemoveField(model_name="movimientos_inventario", name="cantidad_anterior"),
        migrations.RemoveField(model_name="movimientos_inventario", name="cantidad_nueva"),
    ]