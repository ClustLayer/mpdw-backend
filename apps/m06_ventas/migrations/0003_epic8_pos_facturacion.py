"""Épica 8 — POS, pagos, descuentos, devoluciones y consecutivos.

Revision: 0003_epic8_pos_facturacion
"""

import django.db.models.deletion
from django.db import migrations, models


def _numero_a_texto(apps, schema_editor):
    Facturas = apps.get_model("m06_ventas", "Facturas")
    for f in Facturas.objects.all():
        f.numero_factura = str(f.numero_factura).zfill(10)
        f.save(update_fields=["numero_factura"])


class Migration(migrations.Migration):
    dependencies = [
        ("m03_catalogo", "0004_producto_categoria_set_null"),
        ("m05_clientes", "0003_tipos_cliente_color"),
        ("m06_ventas", "0002_detalle_factura"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="consecutivos",
            options={"managed": True},
        ),
        migrations.AddField(
            model_name="tipos_venta",
            name="estado",
            field=models.BooleanField(db_column="estado", default=True),
        ),
        migrations.AlterField(
            model_name="facturas",
            name="id_cliente",
            field=models.ForeignKey(
                blank=True,
                db_column="id_cliente",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="m05_clientes.clientes",
            ),
        ),
        migrations.AlterField(
            model_name="facturas",
            name="serie",
            field=models.CharField(db_column="serie", max_length=30),
        ),
        migrations.AlterField(
            model_name="facturas",
            name="estado",
            field=models.CharField(db_column="estado", default="EMITIDA", max_length=30),
        ),
        migrations.AddField(
            model_name="facturas",
            name="observaciones",
            field=models.TextField(blank=True, db_column="observaciones", default=""),
        ),
        migrations.AddField(
            model_name="facturas",
            name="requiere_factura_electronica",
            field=models.BooleanField(db_column="requiere_factura_electronica", default=False),
        ),
        migrations.AddField(
            model_name="facturas",
            name="requiere_revision_gerencial",
            field=models.BooleanField(db_column="requiere_revision_gerencial", default=False),
        ),
        migrations.AddField(
            model_name="facturas",
            name="margen_negativo",
            field=models.BooleanField(db_column="margen_negativo", default=False),
        ),
        migrations.AddField(
            model_name="facturas",
            name="comprador_nombre",
            field=models.CharField(blank=True, db_column="comprador_nombre", default="", max_length=255),
        ),
        migrations.AddField(
            model_name="facturas",
            name="comprador_documento",
            field=models.CharField(blank=True, db_column="comprador_documento", default="", max_length=30),
        ),
        migrations.AddField(
            model_name="facturas",
            name="comprador_telefono",
            field=models.CharField(blank=True, db_column="comprador_telefono", default="", max_length=20),
        ),
        migrations.AddField(
            model_name="facturas",
            name="comprador_correo",
            field=models.CharField(blank=True, db_column="comprador_correo", default="", max_length=255),
        ),
        migrations.AddField(
            model_name="facturas",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.AddField(
            model_name="detalle_factura",
            name="precio_unitario",
            field=models.DecimalField(db_column="precio_unitario", decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="detalle_factura",
            name="descuento_porcentaje",
            field=models.DecimalField(db_column="descuento_porcentaje", decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="detalle_factura",
            name="descuento_valor",
            field=models.DecimalField(db_column="descuento_valor", decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="detalle_factura",
            name="iva_porcentaje",
            field=models.DecimalField(db_column="iva_porcentaje", decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="detalle_factura",
            name="iva_monto",
            field=models.DecimalField(db_column="iva_monto", decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="detalle_factura",
            name="costo_unitario",
            field=models.DecimalField(db_column="costo_unitario", decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="detalle_factura",
            name="cantidad_devuelta",
            field=models.DecimalField(db_column="cantidad_devuelta", decimal_places=3, default=0, max_digits=14),
        ),
        migrations.CreateModel(
            name="Descuentos_factura",
            fields=[
                ("id_descuento", models.BigAutoField(db_column="id_descuento", primary_key=True, serialize=False)),
                ("tipo_descuento", models.CharField(db_column="tipo_descuento", max_length=20)),
                ("porcentaje", models.DecimalField(db_column="porcentaje", decimal_places=2, default=0, max_digits=5)),
                ("valor", models.DecimalField(db_column="valor", decimal_places=2, default=0, max_digits=14)),
                ("motivo", models.CharField(db_column="motivo", max_length=255)),
                (
                    "id_factura",
                    models.ForeignKey(
                        db_column="id_factura",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="descuentos",
                        to="m06_ventas.facturas",
                    ),
                ),
            ],
            options={"db_table": "Descuentos_factura"},
        ),
        migrations.CreateModel(
            name="Pagos",
            fields=[
                ("id_pago", models.BigAutoField(db_column="id_pago", primary_key=True, serialize=False)),
                ("valor", models.DecimalField(db_column="valor", decimal_places=2, max_digits=14)),
                ("referencia", models.CharField(blank=True, db_column="referencia", default="", max_length=100)),
                (
                    "id_factura",
                    models.ForeignKey(
                        db_column="id_factura",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pagos",
                        to="m06_ventas.facturas",
                    ),
                ),
                (
                    "id_metodo_pago",
                    models.ForeignKey(
                        db_column="id_metodo_pago",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="m06_ventas.metodos_pago",
                    ),
                ),
            ],
            options={"db_table": "Pagos"},
        ),
        migrations.CreateModel(
            name="Devoluciones",
            fields=[
                ("id_devolucion", models.BigAutoField(db_column="id_devolucion", primary_key=True, serialize=False)),
                ("motivo", models.CharField(db_column="motivo", max_length=255)),
                ("total", models.DecimalField(db_column="total", decimal_places=2, max_digits=14)),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                (
                    "id_factura",
                    models.ForeignKey(
                        db_column="id_factura",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="devoluciones",
                        to="m06_ventas.facturas",
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="m01_identidad.usuarios",
                    ),
                ),
            ],
            options={"db_table": "Devoluciones"},
        ),
        migrations.CreateModel(
            name="Detalle_devolucion",
            fields=[
                (
                    "id_detalle_devolucion",
                    models.BigAutoField(db_column="id_detalle_devolucion", primary_key=True, serialize=False),
                ),
                ("cantidad", models.DecimalField(db_column="cantidad", decimal_places=3, max_digits=14)),
                ("valor", models.DecimalField(db_column="valor", decimal_places=2, max_digits=14)),
                (
                    "id_detalle_factura",
                    models.ForeignKey(
                        db_column="id_detalle_factura",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="m06_ventas.detalle_factura",
                    ),
                ),
                (
                    "id_devolucion",
                    models.ForeignKey(
                        db_column="id_devolucion",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lineas",
                        to="m06_ventas.devoluciones",
                    ),
                ),
            ],
            options={"db_table": "Detalle_devolucion"},
        ),
        migrations.AddField(
            model_name="facturas_electronicas",
            name="tipo_nota",
            field=models.CharField(blank=True, db_column="tipo_nota", default="", max_length=30),
        ),
        migrations.AlterField(
            model_name="consecutivos",
            name="serie",
            field=models.CharField(db_column="serie", max_length=30),
        ),
        migrations.AlterField(
            model_name="consecutivos",
            name="id_sede",
            field=models.ForeignKey(
                db_column="id_sede",
                on_delete=django.db.models.deletion.CASCADE,
                to="m02_sedes.sedes",
            ),
        ),
        migrations.AlterField(
            model_name="consecutivos",
            name="ultimo_numero",
            field=models.PositiveIntegerField(db_column="ultimo_numero", default=0),
        ),
        migrations.AlterField(
            model_name="consecutivos",
            name="version",
            field=models.PositiveIntegerField(db_column="version", default=1),
        ),
        migrations.AlterModelTable(
            name="consecutivos",
            table="Consecutivos",
        ),
        migrations.AddConstraint(
            model_name="consecutivos",
            constraint=models.UniqueConstraint(fields=("id_sede", "serie"), name="uq_consecutivo_sede_serie"),
        ),
        migrations.AddIndex(
            model_name="facturas",
            index=models.Index(fields=["estado", "fecha_hora"], name="idx_facturas_estado_fecha"),
        ),
        migrations.AddIndex(
            model_name="facturas",
            index=models.Index(fields=["id_usuario", "fecha_hora"], name="idx_facturas_usuario_fecha"),
        ),
        migrations.AddIndex(
            model_name="facturas",
            index=models.Index(fields=["margen_negativo", "fecha_hora"], name="idx_facturas_margen_fecha"),
        ),
        migrations.AlterField(
            model_name="facturas",
            name="numero_factura",
            field=models.CharField(db_column="numero_factura", max_length=50),
        ),
        migrations.RunPython(_numero_a_texto, migrations.RunPython.noop),
    ]