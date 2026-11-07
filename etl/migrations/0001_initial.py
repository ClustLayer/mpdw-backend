# ==============================================================================
# Migración DDL del Esquema Analítica - MPDW
# SAD Ref: ADR-013, §8.11
# ==============================================================================
from django.db import migrations


def crear_esquema_analitica(apps, schema_editor):
    """SQLite (pytest local): omitir DDL de PostgreSQL."""
    if schema_editor.connection.vendor != "postgresql":
        return
    cursor = schema_editor.connection.cursor()
    cursor.execute(
        """
            CREATE SCHEMA IF NOT EXISTS analitica;

            CREATE TABLE IF NOT EXISTS analitica.ventas_diarias (
                fecha DATE NOT NULL,
                id_sede BIGINT NOT NULL,
                total_ventas NUMERIC(14,2) NOT NULL DEFAULT 0,
                cantidad_facturas INTEGER NOT NULL DEFAULT 0,
                fecha_calculo TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT pk_ventas_diarias PRIMARY KEY (fecha, id_sede)
            );

            CREATE TABLE IF NOT EXISTS analitica.movimientos_diarios (
                fecha DATE NOT NULL,
                id_sede BIGINT NOT NULL,
                tipo_movimiento VARCHAR(20) NOT NULL,
                total_monto NUMERIC(14,2) NOT NULL DEFAULT 0,
                fecha_calculo TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT pk_movimientos_diarios PRIMARY KEY (fecha, id_sede, tipo_movimiento)
            );

            CREATE TABLE IF NOT EXISTS analitica.productos_top (
                fecha DATE NOT NULL,
                id_producto BIGINT NOT NULL,
                cantidad_vendida NUMERIC(14,2) NOT NULL DEFAULT 0,
                total_recaudado NUMERIC(14,2) NOT NULL DEFAULT 0,
                fecha_calculo TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT pk_productos_top PRIMARY KEY (fecha, id_producto)
            );

            CREATE TABLE IF NOT EXISTS analitica.inventario_alerta (
                id_alerta BIGSERIAL PRIMARY KEY,
                fecha DATE NOT NULL,
                id_producto BIGINT NOT NULL,
                id_sede BIGINT NOT NULL,
                cantidad_actual NUMERIC(14,2) NOT NULL,
                nivel_alerta VARCHAR(20) NOT NULL DEFAULT 'BAJO',
                fecha_calculo TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS analitica.corrida_etl (
                id_corrida BIGSERIAL PRIMARY KEY,
                fecha_inicio TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                fecha_fin TIMESTAMPTZ,
                estado VARCHAR(20) NOT NULL,
                filas_afectadas INTEGER NOT NULL DEFAULT 0,
                mensaje_error TEXT,
                duracion_segundos NUMERIC(8,2)
            );

            DO $$
            BEGIN
                IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mpdw_bi') THEN
                    GRANT USAGE ON SCHEMA analitica TO mpdw_bi;
                    GRANT SELECT ON ALL TABLES IN SCHEMA analitica TO mpdw_bi;
                    ALTER DEFAULT PRIVILEGES IN SCHEMA analitica GRANT SELECT ON TABLES TO mpdw_bi;
                END IF;
            END
            $$;
        """
    )


def borrar_esquema_analitica(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP SCHEMA IF EXISTS analitica CASCADE;")


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(crear_esquema_analitica, borrar_esquema_analitica),
    ]

