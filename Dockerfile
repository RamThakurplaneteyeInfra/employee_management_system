# syntax=docker/dockerfile:1

# EMS Backend — multi-stage slim image (Django + Channels ASGI)
# Railway/Render: set builder to Dockerfile; provide env vars via platform (not .env in image).

############################
# Stage 1: build Python deps
############################
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

############################
# Stage 2: runtime
############################
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=ems.settings \
    GUNICORN_WORKERS=3 \
    GUNICORN_TIMEOUT=120 \
    RUN_MIGRATIONS=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appgroup . .
COPY --chown=appuser:appgroup docker-entrypoint.sh /docker-entrypoint.sh

RUN chmod +x /docker-entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/accounts/" || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn ems.asgi:application -k uvicorn.workers.UvicornWorker --workers ${GUNICORN_WORKERS} --bind 0.0.0.0:${PORT} --worker-tmp-dir /dev/shm --timeout ${GUNICORN_TIMEOUT} --log-file -"]
