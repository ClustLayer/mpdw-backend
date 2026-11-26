"""Reduce Auditoria a eventos de seguridad; respalda y elimina el resto en Mongo."""

from django.db import migrations, models

from apps.m13_plataforma.observability.constants import ACCIONES_SEGURIDAD_SQL
from apps.m13_plataforma.observability.migration_backup import backup_rows


def _limpiar_y_respaldar(apps, schema_editor):
    Auditoria = apps.get_model("m10_auditoria", "Auditoria")
    connection = schema_editor.connection
    vendor = connection.vendor

    # RI-16: el trigger bloquea DELETE/UPDATE; se elimina solo durante esta limpieza.
    if vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute('DROP TRIGGER IF EXISTS trg_auditoria_inmutable ON "Auditoria";')

    try:
        no_seg = Auditoria.objects.exclude(accion__in=ACCIONES_SEGURIDAD_SQL)
        filas = list(no_seg)
        if filas:
            backup_rows(filas)
            no_seg.delete()
        Auditoria.objects.filter(accion__iexact="CAMBIO_CONTRASENA").update(
            accion="CAMBIO_PASSWORD"
        )
    finally:
        if vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE OR REPLACE FUNCTION rechazar_modificacion_auditoria()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        RAISE EXCEPTION 'Violacion de inmutabilidad (RI-16): No se permite modificar ni borrar registros de Auditoria';
                    END;
                    $$ LANGUAGE plpgsql;

                    DROP TRIGGER IF EXISTS trg_auditoria_inmutable ON "Auditoria";
                    CREATE TRIGGER trg_auditoria_inmutable
                    BEFORE UPDATE OR DELETE ON "Auditoria"
                    FOR EACH ROW EXECUTE FUNCTION rechazar_modificacion_auditoria();
                    """
                )


class Migration(migrations.Migration):
    dependencies = [
        ("m10_auditoria", "0003_epic11_sin_datos_json"),
        ("m13_plataforma", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_limpiar_y_respaldar, migrations.RunPython.noop),
        migrations.RemoveIndex(model_name="auditoria", name="idx_auditoria_entidad"),
        migrations.RemoveField(model_name="auditoria", name="entidad"),
        migrations.RemoveField(model_name="auditoria", name="id_entidad"),
        migrations.RemoveField(model_name="auditoria", name="user_agent"),
        migrations.RemoveField(model_name="auditoria", name="id_correlacion"),
        migrations.AlterField(
            model_name="auditoria",
            name="motivo",
            field=models.TextField(db_column="motivo"),
        ),
    ]
