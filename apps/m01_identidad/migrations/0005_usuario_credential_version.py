# ==============================================================================
# Version de credencial para invalidar access tokens tras cambio de clave
# ==============================================================================
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m01_identidad", "0004_epic1_autenticacion"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuarios",
            name="credential_version",
            field=models.PositiveIntegerField(default=1, db_column="credential_version"),
        ),
    ]
