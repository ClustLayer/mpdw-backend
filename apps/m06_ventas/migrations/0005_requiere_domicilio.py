from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("m06_ventas", "0004_epic8_seed_catalogos")]

    operations = [
        migrations.AddField(
            model_name="facturas",
            name="requiere_domicilio",
            field=models.BooleanField(db_column="requiere_domicilio", default=False),
        ),
    ]