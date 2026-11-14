import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Proveedores",
            fields=[
                ("id_proveedor", models.BigAutoField(db_column="id_proveedor", primary_key=True, serialize=False)),
                ("nombre", models.CharField(db_column="nombre", max_length=255)),
                ("tipo_documento", models.CharField(db_column="tipo_documento", max_length=20)),
                ("numero_documento", models.CharField(blank=True, db_column="numero_documento", default="", max_length=30)),
                ("contacto_nombre", models.CharField(blank=True, db_column="contacto_nombre", default="", max_length=255)),
                ("contacto_cargo", models.CharField(blank=True, db_column="contacto_cargo", default="", max_length=120)),
                ("telefono", models.CharField(blank=True, db_column="telefono", default="", max_length=20)),
                ("correo", models.EmailField(blank=True, db_column="correo", default="", max_length=255)),
                ("direccion", models.CharField(blank=True, db_column="direccion", default="", max_length=255)),
                ("ciudad", models.CharField(blank=True, db_column="ciudad", default="", max_length=100)),
                ("descripcion", models.TextField(blank=True, db_column="descripcion", default="")),
                ("productos_suministra", models.TextField(blank=True, db_column="productos_suministra", default="")),
                ("estado", models.BooleanField(db_column="estado", default=True)),
                ("version_fila", models.PositiveIntegerField(db_column="version_fila", default=1)),
                ("fecha_registro", models.DateTimeField(auto_now_add=True, db_column="fecha_registro")),
            ],
            options={
                "db_table": "Proveedores",
                "indexes": [
                    models.Index(fields=["nombre"], name="idx_proveedor_nombre"),
                    models.Index(fields=["numero_documento"], name="idx_proveedor_documento"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("numero_documento", ""), _negated=True),  # noqa: E501
                        fields=("numero_documento",),
                        name="uq_proveedor_documento_no_vacio",
                    ),
                ],
            },
        ),
    ]
