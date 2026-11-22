"""Épica 11 — tablas de movimientos de caja y extensión de Reportes_diarios."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("m08_caja", "0003_seed_cuentas_demo"),
        ("m06_ventas", "0006_epic10_facturacion_externa"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Categorias_movimiento",
            fields=[
                ("id_categoria_movimiento", models.BigAutoField(db_column="id_categoria_movimiento", primary_key=True, serialize=False)),
                ("nombre", models.CharField(db_column="nombre", max_length=100)),
                ("tipo_movimiento", models.CharField(db_column="tipo_movimiento", max_length=30)),
                ("descripcion", models.TextField(blank=True, db_column="descripcion", default="")),
                ("estado", models.BooleanField(db_column="estado", default=True)),
                ("version_fila", models.PositiveIntegerField(db_column="version_fila", default=1)),
            ],
            options={"db_table": "Categorias_movimiento"},
        ),
        migrations.AddConstraint(
            model_name="categorias_movimiento",
            constraint=models.UniqueConstraint(fields=("nombre", "tipo_movimiento"), name="uq_categoria_nombre_tipo"),
        ),
        migrations.CreateModel(
            name="Conceptos_movimiento",
            fields=[
                ("id_concepto_movimiento", models.BigAutoField(db_column="id_concepto_movimiento", primary_key=True, serialize=False)),
                ("nombre", models.CharField(db_column="nombre", max_length=255)),
                ("valor_sugerido", models.DecimalField(blank=True, db_column="valor_sugerido", decimal_places=2, max_digits=14, null=True)),
                ("descripcion", models.TextField(blank=True, db_column="descripcion", default="")),
                ("estado", models.BooleanField(db_column="estado", default=True)),
                ("version_fila", models.PositiveIntegerField(db_column="version_fila", default=1)),
                (
                    "id_categoria",
                    models.ForeignKey(db_column="id_categoria", on_delete=django.db.models.deletion.PROTECT, to="m08_caja.categorias_movimiento"),
                ),
            ],
            options={"db_table": "Conceptos_movimiento"},
        ),
        migrations.AddField(model_name="reportes_diarios", name="base_adicional", field=models.DecimalField(db_column="base_adicional", decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="reportes_diarios", name="venta_registrada", field=models.DecimalField(blank=True, db_column="venta_registrada", decimal_places=2, max_digits=14, null=True)),
        migrations.AddField(model_name="reportes_diarios", name="total_ventas", field=models.DecimalField(db_column="total_ventas", decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="reportes_diarios", name="total_transferencias", field=models.DecimalField(db_column="total_transferencias", decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="reportes_diarios", name="total_gastos", field=models.DecimalField(db_column="total_gastos", decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="reportes_diarios", name="total_ahorros", field=models.DecimalField(db_column="total_ahorros", decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="reportes_diarios", name="total_entregas", field=models.DecimalField(db_column="total_entregas", decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="reportes_diarios", name="saldo_caja_efectivo", field=models.DecimalField(blank=True, db_column="saldo_caja_efectivo", decimal_places=2, max_digits=14, null=True)),
        migrations.AddField(model_name="reportes_diarios", name="observaciones", field=models.TextField(blank=True, db_column="observaciones", default="")),
        migrations.AddField(model_name="reportes_diarios", name="observaciones_cierre", field=models.TextField(blank=True, db_column="observaciones_cierre", default="")),
        migrations.AddField(
            model_name="reportes_diarios",
            name="id_usuario_cierre",
            field=models.ForeignKey(
                blank=True,
                db_column="id_usuario_cierre",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reportes_cerrados",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="reportes_diarios",
            name="id_usuario_auditoria",
            field=models.ForeignKey(
                blank=True,
                db_column="id_usuario_auditoria",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reportes_auditados",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(model_name="reportes_diarios", name="fecha_auditoria", field=models.DateTimeField(blank=True, db_column="fecha_auditoria", null=True)),
        migrations.AddField(model_name="reportes_diarios", name="version_fila", field=models.PositiveIntegerField(db_column="version_fila", default=1)),
        migrations.CreateModel(
            name="Gastos_caja",
            fields=[
                ("id_gasto", models.BigAutoField(db_column="id_gasto", primary_key=True, serialize=False)),
                ("valor", models.DecimalField(db_column="valor", decimal_places=2, max_digits=14)),
                ("descripcion", models.TextField(db_column="descripcion")),
                ("anulado", models.BooleanField(db_column="anulado", default=False)),
                ("motivo_anulacion", models.CharField(blank=True, db_column="motivo_anulacion", default="", max_length=255)),
                ("version_fila", models.PositiveIntegerField(db_column="version_fila", default=1)),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                ("id_categoria", models.ForeignKey(db_column="id_categoria", on_delete=django.db.models.deletion.PROTECT, to="m08_caja.categorias_movimiento")),
                ("id_concepto", models.ForeignKey(blank=True, db_column="id_concepto", null=True, on_delete=django.db.models.deletion.SET_NULL, to="m08_caja.conceptos_movimiento")),
                ("id_reporte_diario", models.ForeignKey(db_column="id_reporte_diario", on_delete=django.db.models.deletion.CASCADE, to="m08_caja.reportes_diarios")),
                ("id_usuario", models.ForeignKey(db_column="id_usuario", on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "Gastos"},
        ),
        migrations.CreateModel(
            name="Ahorros",
            fields=[
                ("id_ahorro", models.BigAutoField(db_column="id_ahorro", primary_key=True, serialize=False)),
                ("valor", models.DecimalField(db_column="valor", decimal_places=2, max_digits=14)),
                ("descripcion", models.TextField(db_column="descripcion")),
                ("anulado", models.BooleanField(db_column="anulado", default=False)),
                ("motivo_anulacion", models.CharField(blank=True, db_column="motivo_anulacion", default="", max_length=255)),
                ("version_fila", models.PositiveIntegerField(db_column="version_fila", default=1)),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                ("id_categoria", models.ForeignKey(db_column="id_categoria", on_delete=django.db.models.deletion.PROTECT, to="m08_caja.categorias_movimiento")),
                ("id_concepto", models.ForeignKey(blank=True, db_column="id_concepto", null=True, on_delete=django.db.models.deletion.SET_NULL, to="m08_caja.conceptos_movimiento")),
                ("id_reporte_diario", models.ForeignKey(db_column="id_reporte_diario", on_delete=django.db.models.deletion.CASCADE, to="m08_caja.reportes_diarios")),
                ("id_usuario", models.ForeignKey(db_column="id_usuario", on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "Ahorros"},
        ),
        migrations.CreateModel(
            name="Transferencias_caja",
            fields=[
                ("id_transferencia", models.BigAutoField(db_column="id_transferencia", primary_key=True, serialize=False)),
                ("valor", models.DecimalField(db_column="valor", decimal_places=2, max_digits=14)),
                ("referencia", models.CharField(db_column="referencia", max_length=100)),
                ("observaciones", models.CharField(blank=True, db_column="observaciones", default="", max_length=255)),
                ("origen", models.CharField(db_column="origen", default="MANUAL", max_length=20)),
                ("editable", models.BooleanField(db_column="editable", default=True)),
                ("anulado", models.BooleanField(db_column="anulado", default=False)),
                ("motivo_anulacion", models.CharField(blank=True, db_column="motivo_anulacion", default="", max_length=255)),
                ("version_fila", models.PositiveIntegerField(db_column="version_fila", default=1)),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                ("id_categoria", models.ForeignKey(db_column="id_categoria", on_delete=django.db.models.deletion.PROTECT, to="m08_caja.categorias_movimiento")),
                ("id_cuenta_bancaria", models.ForeignKey(db_column="id_cuenta_bancaria", on_delete=django.db.models.deletion.PROTECT, to="m08_caja.cuentas_bancarias")),
                (
                    "id_pago",
                    models.ForeignKey(blank=True, db_column="id_pago", null=True, on_delete=django.db.models.deletion.SET_NULL, to="m06_ventas.pagos"),
                ),
                ("id_reporte_diario", models.ForeignKey(db_column="id_reporte_diario", on_delete=django.db.models.deletion.CASCADE, to="m08_caja.reportes_diarios")),
                ("id_usuario", models.ForeignKey(db_column="id_usuario", on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "Transferencias"},
        ),
        migrations.CreateModel(
            name="Adiciones_base",
            fields=[
                ("id_adicion", models.BigAutoField(db_column="id_adicion", primary_key=True, serialize=False)),
                ("valor", models.DecimalField(db_column="valor", decimal_places=2, max_digits=14)),
                ("motivo", models.CharField(db_column="motivo", max_length=255)),
                ("anulado", models.BooleanField(db_column="anulado", default=False)),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                ("id_reporte_diario", models.ForeignKey(db_column="id_reporte_diario", on_delete=django.db.models.deletion.CASCADE, to="m08_caja.reportes_diarios")),
                ("id_usuario", models.ForeignKey(db_column="id_usuario", on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "Adiciones_base"},
        ),
        migrations.CreateModel(
            name="Entregas_dinero",
            fields=[
                ("id_entrega", models.BigAutoField(db_column="id_entrega", primary_key=True, serialize=False)),
                ("valor", models.DecimalField(db_column="valor", decimal_places=2, max_digits=14)),
                ("descripcion", models.CharField(db_column="descripcion", max_length=255)),
                ("anulado", models.BooleanField(db_column="anulado", default=False)),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                ("id_reporte_diario", models.ForeignKey(db_column="id_reporte_diario", on_delete=django.db.models.deletion.CASCADE, to="m08_caja.reportes_diarios")),
                ("id_usuario", models.ForeignKey(db_column="id_usuario", on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "Entregas_dinero"},
        ),
        migrations.CreateModel(
            name="Adjuntos_movimiento",
            fields=[
                ("id_adjunto", models.BigAutoField(db_column="id_adjunto", primary_key=True, serialize=False)),
                ("nombre_original", models.CharField(db_column="nombre_original", max_length=255)),
                ("ruta_almacenamiento", models.CharField(db_column="ruta_almacenamiento", max_length=255)),
                ("tipo_mime", models.CharField(db_column="tipo_mime", max_length=100)),
                ("tamano_bytes", models.BigIntegerField(db_column="tamano_bytes")),
                ("hash_integridad", models.CharField(db_column="hash_integridad", max_length=128)),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                ("id_gasto", models.ForeignKey(blank=True, db_column="id_gasto", null=True, on_delete=django.db.models.deletion.CASCADE, to="m08_caja.gastos_caja")),
                ("id_transferencia", models.ForeignKey(blank=True, db_column="id_transferencia", null=True, on_delete=django.db.models.deletion.CASCADE, to="m08_caja.transferencias_caja")),
                ("id_usuario", models.ForeignKey(db_column="id_usuario", on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "Adjuntos_movimiento"},
        ),
    ]