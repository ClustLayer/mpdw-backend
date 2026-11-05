# Epic 2: apellido, telefono, bloqueo optimista y vigencia de contraseña temporal (B-18, HU 07-12)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m01_identidad", "0005_usuario_credential_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuarios",
            name="apellido",
            field=models.CharField(blank=True, db_column="apellido", default="", max_length=255),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="telefono",
            field=models.CharField(blank=True, db_column="telefono", default="", max_length=20),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="contrasena_temporal_expira",
            field=models.DateTimeField(blank=True, db_column="contrasena_temporal_expira", null=True),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.AlterField(
            model_name="usuarios",
            name="nombre",
            field=models.CharField(db_column="nombre", max_length=255),
        ),
    ]
