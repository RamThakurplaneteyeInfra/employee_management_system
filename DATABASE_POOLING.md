# Database Connection Pooling (AWS RDS + Render)

## Overview

The project uses **django-db-connection-pool** so PostgreSQL on AWS RDS (max **79** connections) is not exhausted. With **3 workers**, pool size 15 and max overflow 5 give **60 total connections** (under 79). For **~50 clients**, this is sufficient provided connections are **returned to the pool** after each request.

## Critical: CONN_MAX_AGE = 0

**You must set `CONN_MAX_AGE = 0`** in database settings. With pooling:

- **CONN_MAX_AGE = 0** → Django returns the connection to the pool at the end of each request so it can be reused. The pool does not get exhausted.
- **CONN_MAX_AGE = None** (or a positive value) → Connections can be held and not returned to the pool, so the pool hits its limit (15+5 per worker) and you get `QueuePool limit reached, connection timed out`.

Also set **pool timeout** (e.g. 60 seconds) in `POOL_OPTIONS` so that during bursts the app waits longer for a free connection instead of failing after 30s.

## Approach: 3 workers, 50 clients, RDS 79 max

1. **Total connections** = `3 × (15 + 5) = 60` (under 79).
2. **CONN_MAX_AGE = 0** so each request returns its connection to the pool.
3. **RECYCLE = 3600** so connections are refreshed every hour.
4. **timeout = 60** in POOL_OPTIONS so wait up to 60s for a connection before raising.

## How connections are used

- **Each worker** has its own pool (no sharing across processes).
- **Total DB connections** = `GUNICORN_WORKERS × (POOL_SIZE + MAX_OVERFLOW)`.
- For RDS (79 max): keep total **≤ 65** (reserve rest for admin/migrations/superuser).

## Configuration

### 1. Pool settings (ems/settings.py)

Overridden via environment variables:

| Variable            | Default | Description                                  |
|---------------------|---------|----------------------------------------------|
| `DB_POOL_SIZE`      | 15      | Connections kept per worker                  |
| `DB_MAX_OVERFLOW`   | 5       | Extra connections per worker when pool full  |
| `DB_RECYCLE_SECONDS`| 3600    | Recycle connections after this many seconds |
| `DB_POOL_TIMEOUT`   | 60      | Seconds to wait for a connection from pool  |

**CONN_MAX_AGE** must be **0** (return connection to pool after each request).

**With 3 workers:** 3 × (15 + 5) = **60 max connections** (under RDS 79, suitable for ~50 clients).

### 2. Workers (Procfile / Render)

The app runs with **Gunicorn + UvicornWorker** (ASGI). Each worker is a separate process with its own pool.

| Setting             | Value  | Effect                                      |
|---------------------|--------|---------------------------------------------|
| Workers (default)   | 3      | 3 processes × 20 = 60 max connections      |
| Override            | `GUNICORN_WORKERS` in Render | Change worker count |

### Connection budget (RDS ~79 max)

| Workers | POOL_SIZE | MAX_OVERFLOW | Total connections | Use case              |
|---------|-----------|--------------|-------------------|------------------------|
| 3       | 15        | 5            | **60**            | Recommended (50 clients, RDS 79) |
| 3       | 10        | 10           | 60                | Alternative            |
| 2       | 15        | 5            | 40                | Fewer workers         |
| 4       | 10        | 5            | 60                | More workers          |

## Render setup

### Start command

Use the Procfile or set in Render dashboard:

```bash
gunicorn ems.asgi:application -k uvicorn.workers.UvicornWorker --workers 3 --bind 0.0.0.0:$PORT --worker-tmp-dir /dev/shm --log-file -
```

### Environment variables (Render)

| Variable             | Suggested | Notes                                           |
|----------------------|-----------|-------------------------------------------------|
| `DB_POOL_SIZE`       | 15        | Per-worker pool size                            |
| `DB_MAX_OVERFLOW`    | 5         | Per-worker overflow                             |
| `DB_POOL_TIMEOUT`    | 60        | Wait for connection from pool (seconds)        |
| `DB_RECYCLE_SECONDS` | 3600      | Recycle connections periodically                |
| `GUNICORN_WORKERS`   | 3         | Override in dashboard to change worker count   |

Ensure **CONN_MAX_AGE=0** in settings (not overridden by env) so connections are returned to the pool.

### Max users / concurrency limit

- **Effective limit** = concurrent operations that need a DB connection (HTTP + WebSocket DB access).
- With **60 connections** (3 workers × 20) and **CONN_MAX_AGE=0**, connections are returned after each request, so **~50 clients** can be served without exhausting the pool.
- If you still see `QueuePool limit reached`: ensure **CONN_MAX_AGE=0** (not `None`), ensure **timeout** is set in POOL_OPTIONS (e.g. 60), and that total connections stay **≤ 65** (RDS max 79).

## Install

```bash
pip install django-db-connection-pool[postgresql]
# Or with psycopg2:
pip install django-db-connection-pool[psycopg2]
```

Engine in settings must be `dj_db_conn_pool.backends.postgresql` (not `django_db_conn_pool`).
