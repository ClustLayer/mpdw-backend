# Epic 3 — Roles, permisos y matriz (HU 13–17)
from django.db import migrations, models


def rellenar_nombre_permiso(apps, schema_editor):
    Permisos = apps.get_model("m01_identidad", "Permisos")
    for p in Permisos.objects.all():
        if not (p.nombre or "").strip():
            p.nombre = f"{p.modulo} — {p.accion}"[:100]
            p.save(update_fields=["nombre"])


class Migration(migrations.Migration):

    dependencies = [
        ("m01_identidad", "0007_perfil_datos_personales"),
    ]

    operations = [
        migrations.AlterField(
            model_name="roles",
            name="nombre",
            field=models.CharField(db_column="nombre", max_length=30, unique=True),
        ),
        migrations.AddField(
            model_name="roles",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.AddField(
            model_name="permisos",
            name="nombre",
            field=models.CharField(blank=True, db_column="nombre", default="", max_length=100),
        ),
        migrations.AddField(
            model_name="permisos",
            name="estado",
            field=models.BooleanField(db_column="estado", default=True),
        ),
        migrations.AddField(
            model_name="permisos",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.AlterField(
            model_name="permisos",
            name="modulo",
            field=models.CharField(db_column="modulo", max_length=100),
        ),
        migrations.AlterField(
            model_name="permisos",
            name="accion",
            field=models.CharField(db_column="accion", max_length=50),
        ),
        migrations.AddField(
            model_name="rol_permiso",
            name="permitido",
            field=models.BooleanField(db_column="permitido", default=True),
        ),
        migrations.RunPython(rellenar_nombre_permiso, migrations.RunPython.noop),
    ]
