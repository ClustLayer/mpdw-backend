import django.db.models.deletion
from django.db import migrations, models


def purge_inventario_test_data(apps, schema_editor):
    Movimientos = apps.get_model("m04_inventario", "Movimientos_inventario")
    Inventarios = apps.get_model("m04_inventario", "Inventarios")
    Movimientos.objects.all().delete()
    Inventarios.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("m04_inventario", "0003_costo_unitario"),
        ("m14_proveedores", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(purge_inventario_test_data, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="movimientos_inventario",
            name="proveedor_nombre",
        ),
        migrations.AddField(
            model_name="movimientos_inventario",
            name="id_proveedor",
            field=models.ForeignKey(
                blank=True,
                db_column="id_proveedor",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="m14_proveedores.proveedores",
            ),
        ),
    ]
