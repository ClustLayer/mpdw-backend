import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("m06_ventas", "0005_requiere_domicilio")]

    operations = [
        migrations.AddField(
            model_name="facturas_electronicas",
            name="url_pdf",
            field=models.URLField(blank=True, db_column="url_pdf", default="", max_length=500),
        ),
        migrations.AddField(
            model_name="facturas_electronicas",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.AlterField(
            model_name="facturas_electronicas",
            name="estado",
            field=models.CharField(db_column="estado", default="PENDIENTE", max_length=30),
        ),
    ]