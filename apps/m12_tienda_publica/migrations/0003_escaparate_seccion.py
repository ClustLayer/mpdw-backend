import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("m03_catalogo", "0004_producto_categoria_set_null"),
        ("m12_tienda_publica", "0002_pedidos_web_tabla"),
    ]

    operations = [
        migrations.CreateModel(
            name="Escaparate_seccion",
            fields=[
                ("id_escaparate", models.BigAutoField(db_column="id_escaparate", primary_key=True, serialize=False)),
                ("clave", models.SlugField(db_column="clave", max_length=80, unique=True)),
                ("frase", models.CharField(db_column="frase", max_length=160)),
                ("titulo", models.CharField(db_column="titulo", max_length=160)),
                ("enlace_catalogo", models.CharField(db_column="enlace_catalogo", default="/catalogo", max_length=255)),
                ("color_acento", models.CharField(db_column="color_acento", default="#E11D74", max_length=16)),
                ("orden", models.PositiveIntegerField(db_column="orden", default=0)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
                ("version_fila", models.PositiveIntegerField(db_column="version_fila", default=1)),
            ],
            options={"db_table": "Escaparate_seccion", "ordering": ["orden", "titulo"]},
        ),
        migrations.CreateModel(
            name="Escaparate_producto",
            fields=[
                ("id_escaparate_producto", models.BigAutoField(db_column="id_escaparate_producto", primary_key=True, serialize=False)),
                ("orden", models.PositiveIntegerField(db_column="orden", default=0)),
                (
                    "id_escaparate",
                    models.ForeignKey(
                        db_column="id_escaparate",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="productos",
                        to="m12_tienda_publica.escaparate_seccion",
                    ),
                ),
                (
                    "id_producto",
                    models.ForeignKey(
                        db_column="id_producto",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="m03_catalogo.productos",
                    ),
                ),
            ],
            options={"db_table": "Escaparate_producto"},
        ),
        migrations.AddConstraint(
            model_name="escaparate_producto",
            constraint=models.UniqueConstraint(fields=("id_escaparate", "id_producto"), name="uq_escaparate_producto"),
        ),
    ]