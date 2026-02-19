# Database Connection Pooling (AWS RDS + Render)

## Overview

The project uses **django-db-connection-pool** so PostgreSQL connection slots on AWS RDS (limit ~79) are not exhausted. With **3 workers**, pool settings are tuned so total connections stay under ~65 and the system can handle a predictable **max concurrent load** (effective user/request limit).

## Approach: 3 workers, optimized and limited

1. **Fix total connection budget**  
   `total_connections = 3 × (POOL_SIZE + MAX_OVERFLOW)`. Keep this **≤ 65** so RDS has headroom.

2. **Optimise per-worker pool**  
   - Smaller **POOL_SIZE** = fewer idle connections; **MAX_OVERFLOW** handles bursts.  
   - **CONN_MAX_AGE=0** (in settings) so connections are returned to the pool after each request.  
   - **RECYCLE** so long-lived connections are refreshed.

3. **Limit effective max users/load**  
   The hard limit is **concurrent DB operations** (requests + WebSockets that hit the DB). With 3 workers and a total of ~42 connections (recommended default), you can sustain about **40–50 concurrent request/WS operations** that use the DB. Total “users” can be higher if many are idle; “max users” in practice = how many can be active at once without hitting pool timeouts.

## How connections are used

- **Each worker** has its own pool (no sharing across processes).
- **Total DB connections** = `GUNICORN_WORKERS × (POOL_SIZE + MAX_OVERFLOW)`.
- For RDS (79 max): keep total **≤ 65** (reserve rest for admin/migrations/superuser).

## Configuration

### 1. Pool settings (ems/settings.py)

Overridden via environment variables:

| Variable            | Default | Description                                  |
|---------------------|---------|----------------------------------------------|
| `DB_POOL_SIZE`      | 6       | Connections kept per worker                  |
| `DB_MAX_OVERFLOW`   | 8       | Extra connections per worker when pool full  |
| `DB_RECYCLE_SECONDS`| 3600    | Recycle connections after this many seconds |
| `DB_POOL_TIMEOUT`   | 45      | Seconds to wait for a connection from pool   |

**With 3 workers:** 3 × (6 + 8) = **42 max connections** (optimised, under limit).

### 2. Workers (Procfile / Render)

The app runs with **Gunicorn + UvicornWorker** (ASGI). Each worker is a separate process with its own pool.

| Setting             | Value  | Effect                                      |
|---------------------|--------|---------------------------------------------|
| Workers (default)   | 3      | 3 processes × 14 = 42 max connections      |
| Override            | `GUNICORN_WORKERS` in Render | Change worker count |

### Connection budget (RDS ~79 max)

| Workers | POOL_SIZE | MAX_OVERFLOW | Total connections | Use case              |
|---------|-----------|--------------|-------------------|------------------------|
| 3       | 6         | 8            | **42**            | Recommended default   |
| 3       | 8         | 10           | 54                | Higher concurrency    |
| 3       | 10        | 15           | 75                | Near RDS limit        |
| 2       | 6         | 8            | 28                | Fewer workers         |
| 4       | 5         | 8            | 52                | More workers          |

## Render setup

### Start command

Use the Procfile or set in Render dashboard:

```bash
gunicorn ems.asgi:application -k uvicorn.workers.UvicornWorker --workers 3 --bind 0.0.0.0:$PORT --worker-tmp-dir /dev/shm --log-file -
```

### Environment variables (Render)

| Variable             | Suggested | Notes                                           |
|----------------------|-----------|-------------------------------------------------|
| `DB_POOL_SIZE`       | 6         | Per-worker pool size                            |
| `DB_MAX_OVERFLOW`    | 8         | Per-worker overflow                             |
| `DB_POOL_TIMEOUT`    | 45        | Wait for connection from pool (seconds)        |
| `DB_RECYCLE_SECONDS` | 3600      | Recycle connections periodically                |
| `GUNICORN_WORKERS`   | 3         | Override in dashboard to change worker count   |

### Max users / concurrency limit

- **Effective limit** = number of concurrent operations that need a DB connection (HTTP requests + WebSocket handlers that query DB).
- With **42 connections** (3 workers × 14): plan for **~40–50** such operations at once.
- To support more concurrent users: increase `DB_POOL_SIZE` and/or `DB_MAX_OVERFLOW` **without** exceeding `workers × (POOL_SIZE + MAX_OVERFLOW) ≤ 65`.
- If you see `QueuePool limit reached` / timeouts: either increase pool (within 65 total) or add a higher-level limit (e.g. rate limiting, max concurrent sessions per user).

## Install

```bash
pip install django-db-connection-pool[postgresql]
# Or with psycopg2:
pip install django-db-connection-pool[psycopg2]
```

Engine in settings must be `dj_db_conn_pool.backends.postgresql` (not `django_db_conn_pool`).
