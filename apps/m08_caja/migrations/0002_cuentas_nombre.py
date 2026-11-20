"""Cuentas bancarias: nombre descriptivo y version_fila."""

from django.db import migrations, models


def copiar_nombre_desde_banco(apps, schema_editor):
    Cuentas = apps.get_model("m08_caja", "Cuentas_bancarias")
    for c in Cuentas.objects.all():
        if not (c.nombre or "").strip():
            c.nombre = (c.banco or c.tipo_cuenta or "Cuenta")[:150]
            c.save(update_fields=["nombre"])


class Migration(migrations.Migration):
    dependencies = [("m08_caja", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="cuentas_bancarias",
            name="nombre",
            field=models.CharField(blank=True, db_column="nombre", default="", max_length=150),
        ),
        migrations.AddField(
            model_name="cuentas_bancarias",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.RunPython(copiar_nombre_desde_banco, migrations.RunPython.noop),
    ]