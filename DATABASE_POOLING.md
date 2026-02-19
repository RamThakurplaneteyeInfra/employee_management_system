# Database Connection Pooling (AWS RDS + Render)

## Overview

The project uses **django-db-connection-pool** to avoid exhausting PostgreSQL connection slots on AWS RDS (free tier limit ~79 connections). With 40–50 users, connection reuse depends on both **pool settings** and **ASGI/worker configuration**.

## How connections are used

- **Each worker process** has its own connection pool.
- **Total DB connections** ≈ `workers × (POOL_SIZE + MAX_OVERFLOW)`.
- For RDS (79 max): keep total under **~65** (RDS reserves some for `rds_reserved`).

## Configuration

### 1. Pool settings (ems/settings.py)

Overridden via environment variables:

| Variable            | Default | Description                                  |
|---------------------|---------|----------------------------------------------|
| `DB_POOL_SIZE`      | 5       | Connections kept per process                 |
| `DB_MAX_OVERFLOW`   | 5       | Extra connections when pool is full          |
| `DB_RECYCLE_SECONDS`| 3600    | Recycle connections after this many seconds  |

### 2. Workers (Procfile / Render)

The app runs with **Gunicorn + UvicornWorker** (ASGI) for Channels/WebSockets. Each worker is a separate process with its own pool.

| Setting             | Value  | Effect                                      |
|---------------------|--------|---------------------------------------------|
| Workers (default)   | 3      | 3 processes × 10 connections = 30 max       |
| Override            | `GUNICORN_WORKERS` in Render | Change worker count |

**Example:** 4 workers with `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=5` → 4 × 10 = **40 max connections**.

## Render setup

### Start command

Use the Procfile or set in Render dashboard:

```bash
gunicorn ems.asgi:application -k uvicorn.workers.UvicornWorker --workers 3 --bind 0.0.0.0:$PORT --worker-tmp-dir /dev/shm --log-file -
```

### Environment variables (Render)

| Variable           | Suggested | Notes                                           |
|--------------------|-----------|-------------------------------------------------|
| `DB_POOL_SIZE`     | 5         | Per-worker pool size                            |
| `DB_MAX_OVERFLOW`  | 5         | Per-worker overflow                             |
| `DB_RECYCLE_SECONDS` | 3600    | Recycle connections periodically                |
| `GUNICORN_WORKERS` | 3         | Override in dashboard to change worker count    |

### Connection budget (RDS ~79 max)

| Workers | POOL_SIZE | MAX_OVERFLOW | Max connections |
|---------|-----------|--------------|-----------------|
| 2       | 5         | 5            | 20              |
| 3       | 5         | 5            | 30              |
| 4       | 5         | 5            | 40              |
| 5       | 5         | 5            | 50              |
| 6       | 5         | 5            | 60              |
| 7       | 5         | 5            | 70 (near limit) |

Recommendation: **3–4 workers** with `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=5` → 30–40 connections. Leaves headroom for migrations, admin, or spikes.

## Install

```bash
pip install django-db-connection-pool[postgresql]
# Or with psycopg2:
pip install django-db-connection-pool[psycopg2]
```

Engine in settings must be `dj_db_conn_pool.backends.postgresql` (not `django_db_conn_pool`).
