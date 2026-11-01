# ==============================================================================
# Migración Inicial de Inventarios y Kardex - MPDW
# SAD Ref: M04, ADR-005, RI-04, RI-05, RI-15
# ==============================================================================
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("m01_identidad", "0001_initial"),
        ("m02_sedes", "0001_initial"),
        ("m03_catalogo", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Inventarios",
            fields=[
                ("id_inventario", models.BigAutoField(db_column="id_inventario", primary_key=True, serialize=False)),
                ("cantidad_actual", models.DecimalField(db_column="cantidad_actual", decimal_places=2, default=0, max_digits=14)),
                ("cantidad_reservada", models.DecimalField(db_column="cantidad_reservada", decimal_places=2, default=0, max_digits=14)),
                (
                    "id_producto",
                    models.ForeignKey(
                        db_column="id_producto",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="m03_catalogo.productos",
                    ),
                ),
                (
                    "id_sede",
                    models.ForeignKey(
                        db_column="id_sede",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="m02_sedes.sedes",
                    ),
                ),
            ],
            options={
                "db_table": "Inventarios",
            },
        ),
        migrations.CreateModel(
            name="Movimientos_inventario",
            fields=[
                ("id_movimiento", models.BigAutoField(db_column="id_movimiento", primary_key=True, serialize=False)),
                ("tipo_movimiento", models.CharField(db_column="tipo_movimiento", max_length=30)),
                ("cantidad", models.DecimalField(db_column="cantidad", decimal_places=2, max_digits=14)),
                ("cantidad_anterior", models.DecimalField(db_column="cantidad_anterior", decimal_places=2, max_digits=14)),
                ("cantidad_nueva", models.DecimalField(db_column="cantidad_nueva", decimal_places=2, max_digits=14)),
                ("motivo", models.TextField(db_column="motivo")),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                (
                    "id_inventario",
                    models.ForeignKey(
                        db_column="id_inventario",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movimientos",
                        to="m04_inventario.inventarios",
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_usuario",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="m01_identidad.usuarios",
                    ),
                ),
            ],
            options={
                "db_table": "Movimientos_inventario",
                "ordering": ["-fecha_hora"],
            },
        ),
        migrations.AddConstraint(
            model_name="inventarios",
            constraint=models.UniqueConstraint(fields=("id_producto", "id_sede"), name="uq_inventario_producto_sede"),
        ),
        migrations.AddConstraint(
            model_name="inventarios",
            constraint=models.CheckConstraint(
                condition=models.Q(("cantidad_actual__gte", 0)) & models.Q(("cantidad_reservada__gte", 0)),
                name="chk_stock_no_negativo",
            ),
        ),
        migrations.AddIndex(
            model_name="movimientos_inventario",
            index=models.Index(fields=["id_inventario", "fecha_hora"], name="idx_kardex_inventario_fecha"),
        ),
    ]

