#!/bin/bash
# ==============================================================================
# Script de inicialización de roles y extensiones PostgreSQL para desarrollo local
# SAD Ref: ADR-003, §10.7, §13.1
# ==============================================================================
set -e

# Habilitar extensión pg_trgm en la base de datos principal
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOSQL

# Crear roles diferenciados según el principio de privilegio mínimo
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mpdw_app') THEN
            CREATE ROLE mpdw_app WITH LOGIN CREATEDB PASSWORD '${MPDW_APP_PASSWORD}';
        END IF;

        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mpdw_etl') THEN
            CREATE ROLE mpdw_etl WITH LOGIN PASSWORD '${MPDW_ETL_PASSWORD}';
        END IF;

        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mpdw_migrate') THEN
            CREATE ROLE mpdw_migrate WITH LOGIN SUPERUSER CREATEDB PASSWORD '${MPDW_MIGRATE_PASSWORD}';
        END IF;

        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mpdw_bi') THEN
            CREATE ROLE mpdw_bi WITH LOGIN PASSWORD '${MPDW_BI_PASSWORD}';
        END IF;
    END
    \$\$;

    GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO mpdw_migrate, mpdw_app;
    GRANT ALL ON SCHEMA public TO mpdw_migrate, mpdw_app;
    ALTER SCHEMA public OWNER TO mpdw_migrate;
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO mpdw_app, mpdw_etl, mpdw_bi, mpdw_migrate;
    GRANT USAGE, CREATE ON SCHEMA public TO mpdw_app, mpdw_migrate;
    GRANT USAGE ON SCHEMA public TO mpdw_etl, mpdw_bi;

    ALTER DEFAULT PRIVILEGES FOR ROLE mpdw_migrate IN SCHEMA public
        GRANT ALL ON TABLES TO mpdw_app, mpdw_migrate;
    ALTER DEFAULT PRIVILEGES FOR ROLE mpdw_migrate IN SCHEMA public
        GRANT ALL ON SEQUENCES TO mpdw_app, mpdw_migrate;

    ALTER DEFAULT PRIVILEGES FOR ROLE mpdw_app IN SCHEMA public
        GRANT ALL ON TABLES TO mpdw_app, mpdw_migrate;
    ALTER DEFAULT PRIVILEGES FOR ROLE mpdw_app IN SCHEMA public
        GRANT ALL ON SEQUENCES TO mpdw_app, mpdw_migrate;

    ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
        GRANT ALL ON TABLES TO mpdw_app, mpdw_migrate;
    ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
        GRANT ALL ON SEQUENCES TO mpdw_app, mpdw_migrate;
EOSQL

