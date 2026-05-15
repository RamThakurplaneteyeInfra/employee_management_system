# Asset booking API — merge into your main Django backend

This package contains the **Django app `api`** from the Asset project: models, REST views, URLs, and migrations.

## Contents

| Item | Purpose |
|------|---------|
| `api/` | Django app (copy into your project root next to your other apps) |
| `backend.env.example` | Optional env vars (DB, debug). Rename or merge into your own `.env`. |
| `requirements-asset-api.txt` | Python packages this app expects |

## 1. Copy the app

Place the `api` folder at the same level as your other Django apps (e.g. next to `accounts`, `core`).

**Name conflict:** If your project already has an app named `api`, rename this folder **and** update `api/apps.py` (`name = '...'`), every `import` from `api`, and URL includes — or keep the folder name but use a unique label (advanced). Easiest fix: rename the app to e.g. `asset_booking` with Django’s guidance so migrations stay consistent.

## 2. Install dependencies

Merge into your main `requirements.txt` (or install):

```text
djangorestframework>=3.17,<4.0
django-cors-headers>=4.9,<5.0
```

`psycopg[binary]` and `python-dotenv` are only needed if you use PostgreSQL / dotenv like the original project.

## 3. Register the app

In your main `settings.py`:

```python
INSTALLED_APPS = [
    # ... existing ...
    "rest_framework",
    "corsheaders",
    "api",
]
```

Add CORS middleware **near the top** of `MIDDLEWARE` (before `CommonMiddleware` is typical):

```python
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    # ... rest ...
]
```

## 4. URLs

In your root `urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    # ... your routes ...
    path("api/", include("api.urls")),
]
```

If `path("api/", ...)` is already used, mount under a prefix instead, e.g.:

```python
path("asset-booking/", include("api.urls")),
```

Then set your frontend `VITE_API_BASE_URL` (or equivalent) to that prefix, e.g. `http://localhost:8000/asset-booking`.

### Endpoints (after include at `api/`)

| Method | Path | Notes |
|--------|------|--------|
| GET | `health/` | Health check |
| GET | `calendar-summary/?year=&month=` | Calendar counts |
| GET/POST | `assets/` | List/create (ViewSet) |
| GET/PATCH/DELETE | `assets/<pk>/` | Retrieve/update/delete |

## 5. CORS (if you have a SPA)

Merge with your existing CORS settings, for example:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    # ...
]
# Optional dev convenience (same as original project):
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]
```

## 6. Database

Run migrations **in your main project**:

```bash
python manage.py migrate api
```

The app uses the **default** database. Ensure your `DATABASES` setting is what you want before migrating.

## 7. Admin (optional)

The app registers `Asset` in `api/admin.py`. After `migrate`, you can manage rows in Django admin if `api` is in `INSTALLED_APPS` and you use the admin site.

## Frontend

Point your React/Vite app at the same URL prefix you configured, e.g. `VITE_API_BASE_URL=http://localhost:8000` if routes are under `/api/`.
