from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m03_catalogo", "0002_epic5_catalogo_backoffice"),
    ]

    operations = [
        migrations.AddField(
            model_name="productos",
            name="origen",
            field=models.CharField(
                choices=[("comprado", "Comprado"), ("fabricado", "Fabricado")],
                db_column="origen",
                default="comprado",
                max_length=20,
            ),
        ),
    ]
