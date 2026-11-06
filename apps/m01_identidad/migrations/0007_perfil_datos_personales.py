from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m01_identidad", "0006_epic2_perfil_usuarios"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuarios",
            name="tipo_sangre",
            field=models.CharField(blank=True, default="", max_length=5, db_column="tipo_sangre"),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="fecha_nacimiento",
            field=models.DateField(blank=True, null=True, db_column="fecha_nacimiento"),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="direccion",
            field=models.CharField(blank=True, default="", max_length=255, db_column="direccion"),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="contacto_emergencia_nombre",
            field=models.CharField(blank=True, default="", max_length=255, db_column="contacto_emergencia_nombre"),
        ),
        migrations.AddField(
            model_name="usuarios",
            name="contacto_emergencia_telefono",
            field=models.CharField(blank=True, default="", max_length=20, db_column="contacto_emergencia_telefono"),
        ),
    ]
