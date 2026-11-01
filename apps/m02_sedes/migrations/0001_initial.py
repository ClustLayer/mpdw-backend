from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Sedes",
            fields=[
                ("id_sede", models.BigAutoField(db_column="id_sede", primary_key=True, serialize=False)),
                ("nombre", models.CharField(db_column="nombre", max_length=100)),
                ("direccion", models.CharField(db_column="direccion", max_length=200)),
                ("telefono", models.CharField(blank=True, db_column="telefono", default="", max_length=20)),
                ("ciudad", models.CharField(db_column="ciudad", default="Bogota", max_length=50)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")),
            ],
            options={
                "db_table": "Sedes",
            },
        ),
    ]

