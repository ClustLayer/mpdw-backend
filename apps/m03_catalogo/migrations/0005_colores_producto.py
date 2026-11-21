import django.db.models.deletion
from django.db import migrations, models

PRE = [
    ("Rojo", "#E11D74"),
    ("Azul", "#00A8C5"),
    ("Amarillo", "#FFC93C"),
    ("Verde", "#2E7D32"),
    ("Blanco", "#FFFFFF"),
    ("Negro", "#1A1A1A"),
]


def sembrar_colores(apps, schema_editor):
    Color = apps.get_model("m03_catalogo", "Colores_catalogo")
    for nombre, hex_v in PRE:
        Color.objects.get_or_create(nombre=nombre, defaults={"hex": hex_v, "es_predefinido": True, "estado": True})


class Migration(migrations.Migration):
    dependencies = [("m03_catalogo", "0004_producto_categoria_set_null")]

    operations = [
        migrations.CreateModel(
            name="Colores_catalogo",
            fields=[
                ("id_color", models.BigAutoField(db_column="id_color", primary_key=True, serialize=False)),
                ("nombre", models.CharField(db_column="nombre", max_length=80)),
                ("hex", models.CharField(db_column="hex", max_length=7)),
                ("es_predefinido", models.BooleanField(db_column="es_predefinido", default=False)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
                ("version_fila", models.PositiveIntegerField(db_column="version_fila", default=1)),
            ],
            options={"db_table": "Colores_catalogo"},
        ),
        migrations.CreateModel(
            name="Productos_colores",
            fields=[
                ("id_producto_color", models.BigAutoField(db_column="id_producto_color", primary_key=True, serialize=False)),
                (
                    "id_color",
                    models.ForeignKey(
                        db_column="id_color",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="productos",
                        to="m03_catalogo.colores_catalogo",
                    ),
                ),
                (
                    "id_producto",
                    models.ForeignKey(
                        db_column="id_producto",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="colores_asignados",
                        to="m03_catalogo.productos",
                    ),
                ),
            ],
            options={"db_table": "Productos_colores"},
        ),
        migrations.AddConstraint(
            model_name="colores_catalogo",
            constraint=models.UniqueConstraint(fields=("nombre",), name="uq_color_nombre"),
        ),
        migrations.AddConstraint(
            model_name="productos_colores",
            constraint=models.UniqueConstraint(fields=("id_producto", "id_color"), name="uq_producto_color"),
        ),
        migrations.RunPython(sembrar_colores, migrations.RunPython.noop),
    ]