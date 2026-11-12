import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m03_catalogo", "0003_origen_producto"),
        ("m06_ventas", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Detalle_factura",
            fields=[
                ("id_detalle", models.BigAutoField(db_column="id_detalle", primary_key=True, serialize=False)),
                ("cantidad", models.DecimalField(db_column="cantidad", decimal_places=3, max_digits=14)),
                ("subtotal", models.DecimalField(db_column="subtotal", decimal_places=2, max_digits=14)),
                (
                    "id_factura",
                    models.ForeignKey(
                        db_column="id_factura",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="detalles",
                        to="m06_ventas.facturas",
                    ),
                ),
                (
                    "id_producto",
                    models.ForeignKey(
                        db_column="id_producto",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="m03_catalogo.productos",
                    ),
                ),
            ],
            options={
                "db_table": "Detalle_factura",
            },
        ),
    ]
