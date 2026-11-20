import django.core.validators
from django.db import migrations, models

COLOR_DEFAULT = "#64748B"


def asignar_color_comun(apps, schema_editor):
    Tipos = apps.get_model("m05_clientes", "Tipos_cliente")
    Tipos.objects.filter(nombre__iexact="Común").update(color=COLOR_DEFAULT)
    Tipos.objects.filter(nombre__iexact="Comun").update(color=COLOR_DEFAULT)


class Migration(migrations.Migration):

    dependencies = [
        ("m05_clientes", "0002_epic7_clientes"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipos_cliente",
            name="color",
            field=models.CharField(
                db_column="color",
                default=COLOR_DEFAULT,
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        regex=r"^#[0-9A-Fa-f]{6}$",
                        message="El color debe ser un código hexadecimal (#RRGGBB).",
                    )
                ],
            ),
        ),
        migrations.RunPython(asignar_color_comun, migrations.RunPython.noop),
    ]
