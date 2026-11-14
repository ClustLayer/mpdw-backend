import django.db.models.deletion
from datetime import datetime, time

from django.db import migrations, models
from django.utils import timezone


def migrar_fecha_evento(apps, schema_editor):
    Eventos = apps.get_model("m11_eventos", "Eventos_novedades")
    tz = timezone.get_current_timezone()
    for row in Eventos.objects.all():
        if getattr(row, "fecha_evento", None):
            row.fecha_inicio = timezone.make_aware(datetime.combine(row.fecha_evento, time.min), tz)
        else:
            row.fecha_inicio = timezone.now()
        row.save(update_fields=["fecha_inicio"])


class Migration(migrations.Migration):

    dependencies = [
        ("m01_identidad", "0001_initial"),
        ("m02_sedes", "0001_initial"),
        ("m11_eventos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventos_novedades",
            name="tipo",
            field=models.CharField(db_column="tipo", default="otro", max_length=50),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="fecha_inicio",
            field=models.DateTimeField(db_column="fecha_inicio", null=True),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="fecha_fin",
            field=models.DateTimeField(blank=True, db_column="fecha_fin", null=True),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="impacto",
            field=models.CharField(db_column="impacto", default="Medio", max_length=10),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="areas_afectadas",
            field=models.TextField(blank=True, db_column="areas_afectadas", default=""),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="id_usuario",
            field=models.ForeignKey(
                blank=True,
                db_column="id_usuario",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="m01_identidad.usuarios",
            ),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="estado",
            field=models.BooleanField(db_column="estado", default=True),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="visible_sitio",
            field=models.BooleanField(db_column="visible_sitio", default=False),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="imagen_url",
            field=models.URLField(blank=True, db_column="imagen_url", default="", max_length=500),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="importancia_clave",
            field=models.BooleanField(db_column="importancia_clave", default=False),
        ),
        migrations.AddField(
            model_name="eventos_novedades",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.RunPython(migrar_fecha_evento, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="eventos_novedades",
            name="fecha_evento",
        ),
        migrations.AlterField(
            model_name="eventos_novedades",
            name="fecha_inicio",
            field=models.DateTimeField(db_column="fecha_inicio"),
        ),
        migrations.AlterField(
            model_name="eventos_novedades",
            name="id_sede",
            field=models.ForeignKey(
                blank=True,
                db_column="id_sede",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="m02_sedes.sedes",
            ),
        ),
        migrations.AddIndex(
            model_name="eventos_novedades",
            index=models.Index(fields=["fecha_inicio"], name="idx_evento_fecha_inicio"),
        ),
        migrations.AddIndex(
            model_name="eventos_novedades",
            index=models.Index(fields=["estado", "visible_sitio"], name="idx_evento_publico"),
        ),
    ]
