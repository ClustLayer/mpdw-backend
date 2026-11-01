
# ==============================================================================
# Dockerfile - Mundo Pinturas Diana Web (MPDW) Backend & ETL
# SAD Ref: ADR-004, ADR-012, §13.2
# ==============================================================================

# ------------------------------------------------------------------------------
# Fase 1: Builder
# ------------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv_bin
FROM python:3.13.18-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f AS builder

# Instalar uv binario desde imagen oficial fijada
COPY --from=uv_bin /uv /uv /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copiar manifiesto de dependencias y lockfile
COPY pyproject.toml uv.lock* /app/

# Instalar dependencias de producción en virtualenv /app/.venv
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev --no-install-project; \
    else \
        uv sync --no-dev --no-install-project; \
    fi

# ------------------------------------------------------------------------------
# Fase 2: Runtime
# ------------------------------------------------------------------------------
FROM python:3.13.18-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f AS runtime

ARG COMMIT_SHA="unknown"
LABEL org.opencontainers.image.revision="${COMMIT_SHA}" \
      org.opencontainers.image.title="MPDW Backend & ETL" \
      org.opencontainers.image.vendor="Mundo Pinturas Diana"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000 \
    WEB_CONCURRENCY=2

# Crear usuario y grupo de sistema sin privilegios root
RUN groupadd -g 10001 mpdw && \
    useradd -u 10001 -g mpdw -s /bin/bash -m mpdw

WORKDIR /app

# Copiar entorno virtual precompilado
COPY --from=builder --chown=mpdw:mpdw /app/.venv /app/.venv

# Copiar código fuente de la aplicación
COPY --chown=mpdw:mpdw manage.py /app/
COPY --chown=mpdw:mpdw config/ /app/config/
COPY --chown=mpdw:mpdw contratos/ /app/contratos/
COPY --chown=mpdw:mpdw apps/ /app/apps/
COPY --chown=mpdw:mpdw etl/ /app/etl/

USER mpdw

EXPOSE 8000

# Inicio de gunicorn con workers síncronos enlazado a $PORT (convención Render)
CMD ["sh", "-c", "exec python -m gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --timeout 30 --access-logfile - --error-logfile -"]

