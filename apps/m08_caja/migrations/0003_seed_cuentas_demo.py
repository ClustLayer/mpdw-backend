"""Semilla cuentas de transferencia (POS)."""

from django.db import migrations


CUENTAS = (
    ("Bancolombia Diego", "Bancolombia", "1234567890"),
    ("Nequi Almacén", "Nequi", "3001112233"),
    ("Nequi Andrey", "Nequi", "3002223344"),
    ("Nequi Yoselyn", "Nequi", "3003334455"),
)


def seed(apps, schema_editor):
    Cuentas = apps.get_model("m08_caja", "Cuentas_bancarias")
    for nombre, tipo, numero in CUENTAS:
        Cuentas.objects.get_or_create(
            nombre=nombre,
            defaults={"banco": tipo, "tipo_cuenta": tipo, "numero": numero, "estado": True},
        )


class Migration(migrations.Migration):
    dependencies = [("m08_caja", "0002_cuentas_nombre")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]