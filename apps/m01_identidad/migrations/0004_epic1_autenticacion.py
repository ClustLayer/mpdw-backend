from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m01_identidad", "0003_codigos_2fa_tokens_recuperacion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usuarios",
            name="email",
            field=models.EmailField(db_column="email", max_length=255, unique=True),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="debe_cambiar_password",
            field=models.BooleanField(db_column="debe_cambiar_password", default=False),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="ultimo_acceso",
            field=models.DateTimeField(blank=True, db_column="ultimo_acceso", null=True),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="fecha_actualizacion",
            field=models.DateTimeField(auto_now=True, blank=True, db_column="fecha_actualizacion", null=True),
        ),
        migrations.AddField(
            model_name="sesiones_usuario",
            name="fecha_revocacion",
            field=models.DateTimeField(blank=True, db_column="fecha_revocacion", null=True),
        ),
        migrations.AddField(
            model_name="sesiones_usuario",
            name="mfa_verificada",
            field=models.BooleanField(db_column="mfa_verificada", default=True),
        ),
        migrations.AddField(
            model_name="tokens_recuperacion",
            name="fecha_creacion",
            field=models.DateTimeField(auto_now_add=True, db_column="fecha_creacion", null=True),
        ),
        migrations.AddField(
            model_name="codigos_2fa",
            name="fecha_creacion",
            field=models.DateTimeField(auto_now_add=True, db_column="fecha_creacion", null=True),
        ),
    ]
