from django.db import migrations, models


def marcar_principal_unica(apps, schema_editor):
    Sedes = apps.get_model("m02_sedes", "Sedes")
    if Sedes.objects.filter(es_principal=True).exists():
        return
    primera = Sedes.objects.filter(estado=True).order_by("orden", "id_sede").first()
    if primera is None:
        primera = Sedes.objects.order_by("orden", "id_sede").first()
    if primera is not None:
        primera.es_principal = True
        primera.save(update_fields=["es_principal"])


class Migration(migrations.Migration):
    dependencies = [
        ("m02_sedes", "0003_seed_demo_sedes"),
    ]

    operations = [
        migrations.AddField(
            model_name="sedes",
            name="es_principal",
            field=models.BooleanField(db_column="es_principal", default=False),
        ),
        migrations.RunPython(marcar_principal_unica, migrations.RunPython.noop),
    ]
