import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("m12_tienda_publica", "0001_initial"), ("m02_sedes", "0001_initial")]

    operations = [
        migrations.DeleteModel(name="Pedidos_web"),
        migrations.CreateModel(
            name="Pedidos_web",
            fields=[
                ("id_pedido_web", models.BigAutoField(db_column="id_pedido_web", primary_key=True, serialize=False)),
                ("clave_idempotencia", models.CharField(db_column="clave_idempotencia", max_length=128, unique=True)),
                ("nombre_contacto", models.CharField(db_column="nombre_contacto", max_length=255)),
                ("telefono_contacto", models.CharField(db_column="telefono_contacto", max_length=20)),
                ("direccion_entrega", models.CharField(blank=True, db_column="direccion_entrega", default="", max_length=500)),
                ("observaciones", models.TextField(blank=True, db_column="observaciones", default="")),
                ("items_json", models.JSONField(db_column="items_json")),
                ("total_estimado", models.DecimalField(db_column="total_estimado", decimal_places=2, max_digits=14)),
                ("estado", models.CharField(db_column="estado", default="PENDIENTE", max_length=20)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")),
                (
                    "id_sede",
                    models.ForeignKey(
                        db_column="id_sede",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="m02_sedes.sedes",
                    ),
                ),
            ],
            options={"db_table": "Pedidos_web"},
        ),
    ]