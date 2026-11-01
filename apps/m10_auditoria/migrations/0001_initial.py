# ==============================================================================
# Migración Inicial de Auditoría y Trigger de Inmutabilidad - MPDW
# SAD Ref: M10, ADR-008, RI-16, QA-08
# ==============================================================================
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("m01_identidad", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Auditoria",
            fields=[
                ("id_auditoria", models.BigAutoField(db_column="id_auditoria", primary_key=True, serialize=False)),
                ("accion", models.CharField(db_column="accion", max_length=100)),
                ("entidad", models.CharField(db_column="entidad", max_length=100)),
                ("id_entidad", models.BigIntegerField(db_column="id_entidad")),
                ("datos_antes", models.JSONField(blank=True, db_column="datos_antes", null=True)),
                ("datos_despues", models.JSONField(blank=True, db_column="datos_despues", null=True)),
                ("motivo", models.TextField(db_column="motivo")),
                ("resultado", models.CharField(db_column="resultado", default="EXITO", max_length=20)),
                ("id_correlacion", models.CharField(blank=True, db_column="id_correlacion", default="", max_length=64)),
                ("ip", models.GenericIPAddressField(db_column="ip", default="127.0.0.1")),
                ("user_agent", models.TextField(blank=True, db_column="user_agent", default="")),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_column="fecha_hora")),
                (
                    "id_usuario",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_usuario",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="auditorias",
                        to="m01_identidad.usuarios",
                    ),
                ),
            ],
            options={
                "db_table": "Auditoria",
                "ordering": ["-fecha_hora"],
            },
        ),
        migrations.AddIndex(
            model_name="auditoria",
            index=models.Index(fields=["entidad", "id_entidad", "fecha_hora"], name="idx_auditoria_entidad"),
        ),
        migrations.AddIndex(
            model_name="auditoria",
            index=models.Index(fields=["id_usuario", "fecha_hora"], name="idx_auditoria_usuario"),
        ),
        migrations.AddIndex(
            model_name="auditoria",
            index=models.Index(fields=["accion", "fecha_hora"], name="idx_auditoria_accion"),
        ),
        # RI-16: Trigger PostgreSQL que rechaza UPDATE y DELETE sobre la tabla Auditoria
        migrations.RunSQL(
            sql="""
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
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trg_auditoria_inmutable ON "Auditoria";
            DROP FUNCTION IF EXISTS rechazar_modificacion_auditoria();
            """,
        ),
    ]

