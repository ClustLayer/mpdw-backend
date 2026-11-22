"""Elimina datos_antes/datos_despues (huérfanos de almacenamiento masivo)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("m10_auditoria", "0002_ep13_auditoria_campos"),
    ]

    operations = [
        migrations.RemoveField(model_name="auditoria", name="datos_antes"),
        migrations.RemoveField(model_name="auditoria", name="datos_despues"),
    ]