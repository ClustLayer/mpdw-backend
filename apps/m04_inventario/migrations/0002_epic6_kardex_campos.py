from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("m04_inventario", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="movimientos_inventario",
            name="referencia",
            field=models.CharField(blank=True, db_column="referencia", default="", max_length=80),
        ),
        migrations.AddField(
            model_name="movimientos_inventario",
            name="proveedor_nombre",
            field=models.CharField(blank=True, db_column="proveedor_nombre", default="", max_length=255),
        ),
    ]
