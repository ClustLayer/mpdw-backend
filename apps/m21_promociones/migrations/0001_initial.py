# Generated for Épica 21 Sprint 4

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="Promociones",
            fields=[
                ("id_promocion", models.BigAutoField(db_column="id_promocion", primary_key=True, serialize=False)),
                ("titulo", models.CharField(db_column="titulo", max_length=150)),
                ("tipo", models.CharField(choices=[("promocion", "Promoción"), ("sorteo", "Sorteo")], db_column="tipo", max_length=20)),
                ("descripcion", models.TextField(db_column="descripcion")),
                ("hashtags", models.CharField(blank=True, db_column="hashtags", default="", max_length=500)),
                ("imagen", models.CharField(blank=True, db_column="imagen", default="", max_length=500)),
                ("fecha_inicio", models.DateTimeField(db_column="fecha_inicio")),
                ("fecha_fin", models.DateTimeField(blank=True, db_column="fecha_fin", null=True)),
                (
                    "estado",
                    models.CharField(
                        choices=[("activa", "Activa"), ("pausada", "Pausada")],
                        db_column="estado",
                        default="activa",
                        max_length=20,
                    ),
                ),
                ("version_fila", models.PositiveIntegerField(db_column="version_fila", default=1)),
                ("fecha_registro", models.DateTimeField(auto_now_add=True, db_column="fecha_registro")),
            ],
            options={
                "db_table": "Promociones",
                "indexes": [
                    models.Index(fields=["estado", "fecha_inicio"], name="idx_promo_vigencia"),
                ],
            },
        ),
    ]