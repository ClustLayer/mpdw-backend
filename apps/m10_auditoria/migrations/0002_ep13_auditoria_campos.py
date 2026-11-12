# HU 82: límites de acción e IP (CA 2.1 / ip_origen máx 45)
from django.db import migrations, models


def port_ip_a_texto(apps, schema_editor):
    """PostgreSQL: GenericIPAddressField se almacena como inet; cast a varchar."""
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        'ALTER TABLE "Auditoria" ALTER COLUMN "ip" TYPE varchar(45) USING ("ip"::text);'
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("m10_auditoria", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(port_ip_a_texto, noop_reverse),
        migrations.AlterField(
            model_name="auditoria",
            name="accion",
            field=models.CharField(db_column="accion", max_length=50),
        ),
        migrations.AlterField(
            model_name="auditoria",
            name="ip",
            field=models.CharField(db_column="ip", default="127.0.0.1", max_length=45),
        ),
    ]
