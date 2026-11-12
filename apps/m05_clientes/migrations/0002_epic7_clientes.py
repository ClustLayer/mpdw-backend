# Generated manually — Épica 7 directorio de clientes

from django.db import migrations, models


def semilla_comun(apps, schema_editor):
    Tipos = apps.get_model("m05_clientes", "Tipos_cliente")
    Clientes = apps.get_model("m05_clientes", "Clientes")
    com, created = Tipos.objects.get_or_create(
        nombre="Común",
        defaults={
            "descripcion": "Tipo predeterminado para clientes del mostrador",
            "estado": True,
            "es_tipo_predeterminado": True,
            "version_fila": 1,
        },
    )
    if not created and not com.es_tipo_predeterminado:
        com.es_tipo_predeterminado = True
        com.save(update_fields=["es_tipo_predeterminado"])
    Tipos.objects.exclude(pk=com.pk).update(es_tipo_predeterminado=False)
    for c in Clientes.objects.filter(numero_telefono=""):
        c.numero_telefono = "+573000000001"
        c.save(update_fields=["numero_telefono"])
    sin_tipo = Clientes.objects.filter(id_tipo_cliente__isnull=True)
    for c in sin_tipo:
        c.id_tipo_cliente = com
        c.save(update_fields=["id_tipo_cliente"])


class Migration(migrations.Migration):

    dependencies = [
        ("m05_clientes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipos_cliente",
            name="descripcion",
            field=models.TextField(blank=True, db_column="descripcion", default=""),
        ),
        migrations.AddField(
            model_name="tipos_cliente",
            name="es_tipo_predeterminado",
            field=models.BooleanField(db_column="es_tipo_predeterminado", default=False),
        ),
        migrations.AddField(
            model_name="tipos_cliente",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.RenameField(
            model_name="clientes",
            old_name="telefono",
            new_name="numero_telefono",
        ),
        migrations.RenameField(
            model_name="clientes",
            old_name="email",
            new_name="correo",
        ),
        migrations.AlterField(
            model_name="clientes",
            name="nombre",
            field=models.CharField(db_column="nombre", max_length=255),
        ),
        migrations.AlterField(
            model_name="clientes",
            name="numero_telefono",
            field=models.CharField(db_column="numero_telefono", default="", max_length=20),
        ),
        migrations.AddField(
            model_name="clientes",
            name="apellido",
            field=models.CharField(blank=True, db_column="apellido", default="", max_length=255),
        ),
        migrations.AddField(
            model_name="clientes",
            name="ciudad",
            field=models.CharField(blank=True, db_column="ciudad", default="", max_length=100),
        ),
        migrations.AddField(
            model_name="clientes",
            name="tiene_whatsapp",
            field=models.BooleanField(db_column="tiene_whatsapp", default=False),
        ),
        migrations.AddField(
            model_name="clientes",
            name="observaciones",
            field=models.TextField(blank=True, db_column="observaciones", default=""),
        ),
        migrations.AddField(
            model_name="clientes",
            name="version_fila",
            field=models.PositiveIntegerField(db_column="version_fila", default=1),
        ),
        migrations.AlterField(
            model_name="clientes",
            name="correo",
            field=models.EmailField(blank=True, db_column="correo", default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="clientes",
            name="direccion",
            field=models.CharField(blank=True, db_column="direccion", default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="clientes",
            name="documento",
            field=models.CharField(blank=True, db_column="documento", default="", max_length=30),
        ),
        migrations.RunPython(semilla_comun, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="clientes",
            name="numero_telefono",
            field=models.CharField(db_column="numero_telefono", max_length=20),
        ),
        migrations.RemoveConstraint(
            model_name="clientes",
            name="chk_consentimiento_fecha",
        ),
        migrations.AddConstraint(
            model_name="clientes",
            constraint=models.CheckConstraint(
                condition=models.Q(("consentimiento_datos", False), ("fecha_consentimiento__isnull", False), _connector="OR"),
                name="chk_consentimiento_fecha",
            ),
        ),
        migrations.AddConstraint(
            model_name="clientes",
            constraint=models.UniqueConstraint(
                condition=models.Q(("documento", ""), _negated=True),
                fields=("documento",),
                name="uq_cliente_documento_no_vacio",
            ),
        ),
        migrations.AddIndex(
            model_name="clientes",
            index=models.Index(fields=["numero_telefono"], name="idx_cliente_telefono"),
        ),
        migrations.AddIndex(
            model_name="clientes",
            index=models.Index(fields=["correo"], name="idx_cliente_correo"),
        ),
        migrations.AddIndex(
            model_name="clientes",
            index=models.Index(fields=["documento"], name="idx_cliente_documento"),
        ),
        migrations.AddIndex(
            model_name="clientes",
            index=models.Index(fields=["nombre"], name="idx_cliente_nombre"),
        ),
    ]
