# Correcciones iteración 3 (HU MPDW 01 01)

## Calidad

- Ruff: imports y variables no usadas corregidos en `tests/unit/test_epic1_auth.py`.

## Base de datos local

- Conexión Supabase validada con pooler `aws-0-us-east-1`, usuario `postgres.ymxlkdzkpskvgrpdggjp`, puerto 6543 (`.env` local, no versionado).

## Validación local

- Puertas 0–4, 6–9 verificadas (Ruff, Mypy, import-linter, unit+cobertura, OpenAPI diff, Bandit, Docker build).
- Puerta 5 (integración/concurrencia) ejecutada contra PostgreSQL efímero en Docker con `MPDW_TEST_USE_POSTGRES=true`.
- `pip-audit` bloqueado por política de Windows en este entorno; CI en Ubuntu lo ejecuta.
