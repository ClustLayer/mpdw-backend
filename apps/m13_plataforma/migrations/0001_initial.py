# ==============================================================================
# Migración de Infraestructura, Caché y Privilegios Mínimos - MPDW
# SAD Ref: ADR-003, ADR-010, §10.7, §13.5
# ==============================================================================
from django.db import migrations


def aplicar_privilegios_y_cache(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    if schema_editor.connection.vendor != "postgresql":
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS django_cache ("
            "cache_key varchar(255) PRIMARY KEY, "
            "value text, "
            "expires timestamp"
            ");"
        )
        return

    sql = """
    -- 1. Crear tabla de caché de throttling
    CREATE TABLE IF NOT EXISTS django_cache (
        cache_key varchar(255) PRIMARY KEY,
        value text,
        expires timestamp with time zone
    );

    -- 2. Privilegios mínimos para rol mpdw_app
    DO $$
    BEGIN
        IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mpdw_app') THEN
            GRANT USAGE ON SCHEMA public TO mpdw_app;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO mpdw_app;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mpdw_app;
            GRANT ALL PRIVILEGES ON TABLE django_cache TO mpdw_app;

            -- Sin DELETE en tablas financieras e inmutables
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'Facturas') THEN
                REVOKE DELETE ON TABLE "Facturas" FROM mpdw_app;
            END IF;
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'Historial_precios') THEN
                REVOKE DELETE ON TABLE "Historial_precios" FROM mpdw_app;
            END IF;
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'Movimientos_inventario') THEN
                REVOKE DELETE ON TABLE "Movimientos_inventario" FROM mpdw_app;
            END IF;
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'Cierres_caja') THEN
                REVOKE DELETE ON TABLE "Cierres_caja" FROM mpdw_app;
            END IF;
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'Auditoria') THEN
                REVOKE DELETE, UPDATE ON TABLE "Auditoria" FROM mpdw_app;
            END IF;

            -- Sin acceso al esquema de analitica
            IF EXISTS (SELECT FROM information_schema.schemata WHERE schema_name = 'analitica') THEN
                REVOKE ALL ON SCHEMA analitica FROM mpdw_app;
            END IF;
        END IF;
    END
    $$;
    """
    cursor.execute(sql)


def revertir_privilegios_y_cache(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute("DROP TABLE IF EXISTS django_cache;")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("m01_identidad", "0001_initial"),
        ("m03_catalogo", "0001_initial"),
        ("m04_inventario", "0001_initial"),
        ("m10_auditoria", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(aplicar_privilegios_y_cache, reverse_code=revertir_privilegios_y_cache),
    ]

