# ==============================================================================
# Migración Inicial de Catálogo de Productos y Precios - MPDW
# SAD Ref: M03, ADR-005, G-08, RI-02, RI-26, IX-1
# ==============================================================================
import django.contrib.postgres.indexes
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("m01_identidad", "0001_initial"),
    ]

    operations = [
        TrigramExtension(),
        migrations.CreateModel(
            name="Categorias_producto",
            fields=[
                ("id_categoria", models.BigAutoField(db_column="id_categoria", primary_key=True, serialize=False)),
                ("nombre", models.CharField(db_column="nombre", max_length=100, unique=True)),
                ("descripcion", models.CharField(blank=True, db_column="descripcion", default="", max_length=200)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
            ],
            options={
                "db_table": "Categorias_producto",
            },
        ),
        migrations.CreateModel(
            name="Marcas",
            fields=[
                ("id_marca", models.BigAutoField(db_column="id_marca", primary_key=True, serialize=False)),
                ("nombre", models.CharField(db_column="nombre", max_length=100, unique=True)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
            ],
            options={
                "db_table": "Marcas",
            },
        ),
        migrations.CreateModel(
            name="Tipos_producto",
            fields=[
                ("id_tipo_producto", models.BigAutoField(db_column="id_tipo_producto", primary_key=True, serialize=False)),
                ("nombre", models.CharField(db_column="nombre", max_length=100, unique=True)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
            ],
            options={
                "db_table": "Tipos_producto",
            },
        ),
        migrations.CreateModel(
            name="Productos",
            fields=[
                ("id_producto", models.BigAutoField(db_column="id_producto", primary_key=True, serialize=False)),
                ("codigo_producto", models.CharField(db_column="codigo_producto", max_length=50, unique=True)),
                ("codigo_barras", models.CharField(blank=True, db_column="codigo_barras", max_length=50, null=True, unique=True)),
                ("nombre", models.CharField(db_column="nombre", max_length=200)),
                ("descripcion", models.TextField(blank=True, db_column="descripcion", default="")),
                ("precio_venta", models.DecimalField(db_column="precio_venta", decimal_places=2, max_digits=14)),
                ("inventario_habilitado", models.BooleanField(db_column="inventario_habilitado", default=True)),
                ("version", models.IntegerField(db_column="version", default=1)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")),
                (
                    "id_categoria",
                    models.ForeignKey(
                        db_column="id_categoria",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="m03_catalogo.categorias_producto",
                    ),
                ),
                (
                    "id_marca",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_marca",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="m03_catalogo.marcas",
                    ),
                ),
                (
                    "id_tipo_producto",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_tipo_producto",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="m03_catalogo.tipos_producto",
                    ),
                ),
            ],
            options={
                "db_table": "Productos",
            },
        ),
        migrations.CreateModel(
            name="Historial_precios",
            fields=[
                ("id_historial", models.BigAutoField(db_column="id_historial", primary_key=True, serialize=False)),
                ("precio_anterior", models.DecimalField(db_column="precio_anterior", decimal_places=2, max_digits=14)),
                ("precio_nuevo", models.DecimalField(db_column="precio_nuevo", decimal_places=2, max_digits=14)),
                ("motivo", models.TextField(db_column="motivo")),
                ("fecha_cambio", models.DateTimeField(auto_now_add=True, db_column="fecha_cambio")),
                ("fecha_fin", models.DateTimeField(blank=True, db_column="fecha_fin", null=True)),
                (
                    "id_producto",
                    models.ForeignKey(
                        db_column="id_producto",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historial_precios",
                        to="m03_catalogo.productos",
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
                "db_table": "Historial_precios",
            },
        ),
        migrations.AddIndex(
            model_name="productos",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["nombre"], name="idx_productos_nombre_trgm", opclasses=["gin_trgm_ops"]
            ),
        ),
        migrations.AddConstraint(
            model_name="historial_precios",
            constraint=models.UniqueConstraint(
                condition=models.Q(("fecha_fin__isnull", True)),
                fields=("id_producto",),
                name="uq_historial_precio_vigente",
            ),
        ),
    ]

