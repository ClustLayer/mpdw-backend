from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("m03_catalogo", "0003_origen_producto"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productos",
            name="id_categoria",
            field=models.ForeignKey(
                blank=True,
                db_column="id_categoria",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="m03_catalogo.categorias_producto",
            ),
        ),
    ]
