# API Caching (GET responses)

GET responses are cached in Redis (same instance as WebSocket channels) to reduce database load and improve performance.

## How it works

- **Middleware** (`ems.middleware.CacheGetMiddleware`): For every GET request, the response is cached keyed by path + query string + user. Next time the same user hits the same GET URL, the response is served from cache (no view or DB).
- **Timeout**: Cached GET responses expire after **5 minutes** (configurable via env `CACHE_GET_TIMEOUT`, in seconds).
- **Invalidation**: When data is created or updated (`post_save` on relevant models), the cache for the affected API prefix is cleared so the next GET returns fresh data.

## Configuration

- **Redis**: Uses `REDIS_URL` (same as Channels). If `REDIS_URL` is not set (e.g. local dev), the cache backend falls back to in-memory `LocMemCache`.
- **Skip paths**: `/admin/`, `/static/`, `/media/` are not cached.

## Invalidation prefixes

| App / data        | Prefix(es) invalidated on create/update      |
|-------------------|----------------------------------------------|
| events            | `eventsapi`                                  |
| Messaging         | `messaging`                                  |
| task_management   | `tasks`                                      |
| notifications     | `notifications`                             |
| adminpanel        | `adminapi`                                   |
| accounts          | `accounts`                                   |
| QuaterlyReports   | `getMonthlySchedule`, `getUserEntries`, etc. |

## Optional env

- `CACHE_GET_TIMEOUT`: Cache TTL in seconds (default `300`).

## Adding new models

To invalidate cache when a new model is created/updated, register it in `ems/cache_invalidation.py`: add the model to `models_to_watch` and, if the app is new, add an entry to `PREFIXES_BY_APP`.
