from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m11_eventos", "0002_epic12_eventos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eventos_novedades",
            name="imagen_url",
            field=models.CharField(blank=True, db_column="imagen_url", default="", max_length=500),
        ),
    ]
