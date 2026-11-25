"""Semilla mínima de categorías de movimiento para Conceptos de caja."""

from django.db import migrations


def seed(apps, schema_editor):
    Cat = apps.get_model("m08_caja", "Categorias_movimiento")
    defaults = (
        ("Insumos operativos", "Gasto", "Gastos frecuentes del punto de venta"),
        ("Servicios", "Gasto", "Servicios públicos y terceros"),
        ("Traslado a banco", "Transferencia", "Transferencias desde caja"),
        ("Reserva", "Ahorro", "Ahorros o reservas de efectivo"),
    )
    for nombre, tipo, desc in defaults:
        if not Cat.objects.filter(nombre=nombre, tipo_movimiento=tipo).exists():
            Cat.objects.create(
                nombre=nombre,
                tipo_movimiento=tipo,
                descripcion=desc,
                estado=True,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("m08_caja", "0004_epic11_caja_movimientos"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
