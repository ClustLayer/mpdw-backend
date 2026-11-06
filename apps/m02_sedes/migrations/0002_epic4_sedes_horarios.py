import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("m02_sedes", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="sedes",
            name="whatsapp",
            field=models.CharField(blank=True, default="", max_length=20, db_column="whatsapp"),
        ),
        migrations.AddField(
            model_name="sedes",
            name="maps_url",
            field=models.CharField(blank=True, default="", max_length=500, db_column="maps_url"),
        ),
        migrations.AddField(
            model_name="sedes",
            name="map_query",
            field=models.CharField(blank=True, default="", max_length=255, db_column="map_query"),
        ),
        migrations.AddField(
            model_name="sedes",
            name="orden",
            field=models.PositiveIntegerField(default=10, db_column="orden"),
        ),
        migrations.AddField(
            model_name="sedes",
            name="version_fila",
            field=models.PositiveIntegerField(default=1, db_column="version_fila"),
        ),
        migrations.AddField(
            model_name="sedes",
            name="id_usuario_responsable",
            field=models.ForeignKey(
                blank=True,
                db_column="id_usuario_responsable",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sedes_responsable",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="sedes",
            name="nombre",
            field=models.CharField(max_length=255, db_column="nombre"),
        ),
        migrations.AlterField(
            model_name="sedes",
            name="direccion",
            field=models.CharField(max_length=255, db_column="direccion"),
        ),
        migrations.CreateModel(
            name="Sede_horario",
            fields=[
                ("id_horario", models.BigAutoField(db_column="id_horario", primary_key=True, serialize=False)),
                ("dia_semana", models.PositiveSmallIntegerField(db_column="dia_semana")),
                ("hora_apertura", models.TimeField(blank=True, db_column="hora_apertura", null=True)),
                ("hora_cierre", models.TimeField(blank=True, db_column="hora_cierre", null=True)),
                ("cerrado", models.BooleanField(db_column="cerrado", default=False)),
                (
                    "id_sede",
                    models.ForeignKey(
                        db_column="id_sede",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="horarios",
                        to="m02_sedes.sedes",
                    ),
                ),
            ],
            options={"db_table": "Sede_horario"},
        ),
        migrations.AddConstraint(
            model_name="sede_horario",
            constraint=models.UniqueConstraint(
                fields=("id_sede", "dia_semana"), name="uq_sede_horario_dia"
            ),
        ),
    ]
