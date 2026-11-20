"""Épica 9 — ampliar Entregas/Mensajeros, Historial_entregas y restricción activa."""

import datetime
from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def backfill_mensajeros(apps, schema_editor):
    Mensajeros = apps.get_model("m07_domicilios", "Mensajeros")
    hoy = datetime.date.today()
    for m in Mensajeros.objects.all():
        if not m.apellido:
            m.apellido = "N/A"
        if not m.fecha_inicio:
            m.fecha_inicio = hoy
        if m.tarifa_promedio is None:
            m.tarifa_promedio = Decimal("0")
        m.save()


def seed_domicilio_tipo(apps, schema_editor):
    Tipos = apps.get_model("m06_ventas", "Tipos_venta")
    Tipos.objects.get_or_create(nombre="Domicilio", defaults={"estado": True})


class Migration(migrations.Migration):
    dependencies = [
        ("m06_ventas", "0004_epic8_seed_catalogos"),
        ("m07_domicilios", "0001_initial"),
        ("m01_identidad", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="entregas", name="uq_entrega_activa_por_factura"),
        migrations.RenameField(model_name="entregas", old_name="direccion_entrega", new_name="direccion"),
        migrations.AlterField(
            model_name="entregas",
            name="direccion",
            field=models.CharField(db_column="direccion", max_length=255),
        ),
        migrations.AlterField(
            model_name="entregas",
            name="estado",
            field=models.CharField(db_column="estado", default="PENDIENTE", max_length=30),
        ),
        migrations.AddField(
            model_name="entregas",
            name="telefono_contacto",
            field=models.CharField(blank=True, db_column="telefono_contacto", default="", max_length=20),
        ),
        migrations.AddField(
            model_name="entregas",
            name="valor_cobrado_cliente",
            field=models.DecimalField(db_column="valor_cobrado_cliente", decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="entregas",
            name="valor_pagado_mensajero",
            field=models.DecimalField(db_column="valor_pagado_mensajero", decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="entregas",
            name="observaciones",
            field=models.CharField(blank=True, db_column="observaciones", default="", max_length=500),
        ),
        migrations.AddField(
            model_name="entregas",
            name="fecha_asignacion",
            field=models.DateTimeField(blank=True, db_column="fecha_asignacion", null=True),
        ),
        migrations.AddField(
            model_name="entregas",
            name="fecha_salida",
            field=models.DateTimeField(blank=True, db_column="fecha_salida", null=True),
        ),
        migrations.AddField(
            model_name="entregas",
            name="fecha_entrega",
            field=models.DateTimeField(blank=True, db_column="fecha_entrega", null=True),
        ),
        migrations.AddField(
            model_name="entregas",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.AlterField(
            model_name="mensajeros",
            name="nombre",
            field=models.CharField(db_column="nombre", max_length=255),
        ),
        migrations.AddField(
            model_name="mensajeros",
            name="apellido",
            field=models.CharField(db_column="apellido", default="N/A", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="mensajeros",
            name="fecha_inicio",
            field=models.DateField(db_column="fecha_inicio", default=datetime.date(2020, 1, 1)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="mensajeros",
            name="tarifa_promedio",
            field=models.DecimalField(db_column="tarifa_promedio", decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="mensajeros",
            name="observaciones",
            field=models.TextField(blank=True, db_column="observaciones", default=""),
        ),
        migrations.AddField(
            model_name="mensajeros",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.RunPython(backfill_mensajeros, migrations.RunPython.noop),
        migrations.CreateModel(
            name="Historial_entregas",
            fields=[
                ("id_historial", models.BigAutoField(db_column="id_historial", primary_key=True, serialize=False)),
                ("estado_anterior", models.CharField(blank=True, db_column="estado_anterior", max_length=30, null=True)),
                ("estado_nuevo", models.CharField(db_column="estado_nuevo", max_length=30)),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                ("observaciones", models.TextField(blank=True, db_column="observaciones", default="")),
                (
                    "id_entrega",
                    models.ForeignKey(
                        db_column="id_entrega",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historial",
                        to="m07_domicilios.entregas",
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
            options={
                "db_table": "Historial_entregas",
                "ordering": ["-fecha_hora"],
            },
        ),
        migrations.AddConstraint(
            model_name="entregas",
            constraint=models.UniqueConstraint(
                condition=models.Q(("estado__in", ["PENDIENTE", "ASIGNADO", "EN_CAMINO"])),
                fields=("id_factura",),
                name="uq_entrega_activa_por_factura",
            ),
        ),
        migrations.RunPython(seed_domicilio_tipo, migrations.RunPython.noop),
    ]