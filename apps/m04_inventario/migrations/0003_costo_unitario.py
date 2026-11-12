from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m04_inventario", "0002_epic6_kardex_campos"),
    ]

    operations = [
        migrations.AddField(
            model_name="movimientos_inventario",
            name="costo_unitario",
            field=models.DecimalField(
                blank=True,
                db_column="costo_unitario",
                decimal_places=2,
                max_digits=14,
                null=True,
            ),
        ),
    ]
