# Alerts & Announcements – API testing reference (Postman)

**Base URL:** `{{baseurl}}/alertsapi/`  
**Auth:** All endpoints require a **logged-in user** (session/cookie).  
**Content-Type:** `application/json` for POST/PUT/PATCH bodies.

---

## 1. Alert types (read-only)

<!-- | Method | URL | Description |
|--------|-----|-------------|
| GET | `{{baseurl}}/alertsapi/alert-types/` | List all alert types |
| GET | `{{baseurl}}/alertsapi/alert-types/<id>/` | Retrieve one alert type |

### GET – List alert types

**URL:** `{{baseurl}}/alertsapi/alert-types/`

**Success (200):** Array of `{ "id": 1, "type_name": "System" }, ...`

--- -->

## 2. Alerts (CRUD)

<!-- | Method | URL | Description |
|--------|-----|-------------|
| GET | `{{baseurl}}/alertsapi/alerts/` | List all alerts |
| GET | `{{baseurl}}/alertsapi/alerts/<id>/` | Retrieve one alert |
| POST | `{{baseurl}}/alertsapi/alerts/` | Create an alert |
| PUT | `{{baseurl}}/alertsapi/alerts/<id>/` | Full update |
| PATCH | `{{baseurl}}/alertsapi/alerts/<id>/` | Partial update |
| DELETE | `{{baseurl}}/alertsapi/alerts/<id>/` | Delete an alert |

### GET – List alerts

**URL:** `{{baseurl}}/alertsapi/alerts/`

**Success (200):** Array of alert objects. Each includes (all datetime fields in IST, format **d/m/y H:M:S**):

- `id`, `alert_title`, `alert_type` (type name), `alert_severity` (`"high"` \| `"medium"` \| `"low"`)
- `creator_name` (full name from Profile; `alert_creator` username not in response)
- `details`
- `created_at` (IST, e.g. `09/03/2026 14:30:00`)
- `close_at` (IST; null if not closed)
- `resolved_by_name` (full name or null; `resolved_by` username not in response)
- `closed_by` (IST formatted, e.g. `15/03/2026 10:30:00`)
- `status` (status name, e.g. PENDING)

### POST – Create alert

**URL:** `{{baseurl}}/alertsapi/alerts/`  
**Method:** `POST`  
**Headers:** `Content-Type: application/json`

**Body (example):**

```json
{
  "alert_title": "Server maintenance scheduled",
  "alert_type": "System",
  "alert_severity": "high",
  "resolved_by": "admin",
  "closed_by": "2026-03-15T10:30:00",
  "details": "Maintenance window 2–4 AM IST.",
  "status": "PENDING"
}
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| alert_title | string | Yes | Title of the alert |
| alert_type | string | Yes | **Alert type name** (must exist in alert_types, e.g. `"System"`) |
| alert_severity | string | Yes | One of: `"high"`, `"medium"`, `"low"` |
| resolved_by | string | Yes | **Username** of user who resolved/closed the alert (must exist) |
| closed_by | string | Yes | **DateTime** when closed; ISO 8601 (e.g. `"2026-03-15T10:30:00"` or `"2026-03-15T16:00:00+05:30"`) |
| details | string | No | Additional details |
| status | string | No | **Task status name** (e.g. `"PENDING"`, `"INPROCESS"`, `"COMPLETED"`); optional |

**Note:** `alert_creator` is set automatically from the logged-in user and is not in the request body or GET response.

**Success (201):** Created alert object (same shape as GET list/detail: `created_at`, `close_at`, `closed_by` in IST d/m/y H:M:S; no `alert_creator` or `resolved_by` in response).

### PATCH – Update alert (e.g. close or resolve)

**URL:** `{{baseurl}}/alertsapi/alerts/<id>/`  
**Method:** `PATCH`  
**Headers:** `Content-Type: application/json`

**Body (example – close/resolve):**

```json
{
  "close_at": "2026-03-15T10:30:00",
  "resolved_by": "admin",
  "closed_by": "2026-03-15T10:30:00",
  "status": "COMPLETED"
}
```

Any subset of writable fields can be sent. `closed_by` in the request is ISO 8601; in the GET response it is returned as IST in **d/m/y H:M:S** format. -->

### DELETE – Delete alert

<!-- **URL:** `{{baseurl}}/alertsapi/alerts/<id>/`  
**Method:** `DELETE`

**Success (204):** No content. -->

---

## 3. Announcement types (read-only)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `{{baseurl}}/alertsapi/announcement-types/` | List all announcement types |
| GET | `{{baseurl}}/alertsapi/announcement-types/<id>/` | Retrieve one announcement type |

### GET – List announcement types

**URL:** `{{baseurl}}/alertsapi/announcement-types/`

**Success (200):** Array of `{ "id": 1, "type_name": "Product" }, ...`

---

## 4. Announcements (CRUD)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `{{baseurl}}/alertsapi/announcements/` | List all announcements |
| GET | `{{baseurl}}/alertsapi/announcements/<id>/` | Retrieve one announcement |
| POST | `{{baseurl}}/alertsapi/announcements/` | Create an announcement |
| PUT | `{{baseurl}}/alertsapi/announcements/<id>/` | Full update |
| PATCH | `{{baseurl}}/alertsapi/announcements/<id>/` | Partial update |
| DELETE | `{{baseurl}}/alertsapi/announcements/<id>/` | Delete an announcement |

### GET – List announcements

**URL:** `{{baseurl}}/alertsapi/announcements/`

**Success (200):** Array of announcement objects. Each includes:

- `id`, `announcement` (text), `created_by` (username), `creator_name` (full name)
- `type` (type name), `product` (product name or null), `percentage` (int or null)
- `created_at`, `created_at_ist` (IST formatted)

### POST – Create announcement

**URL:** `{{baseurl}}/alertsapi/announcements/`  
**Method:** `POST`  
**Headers:** `Content-Type: application/json`

**Body (example):**

```json
{
  "announcement": "New product launch next week.",
  "type": "Product",
  "product": "Product A",
  "percentage": 15
}
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| announcement | string | Yes | Announcement text |
| type | string | Yes | **Announcement type name** (must exist in announcement_types) |
| product | string | No | **Product name** (must exist in Product table); omit or null for none |
| percentage | int | No | Optional percentage (e.g. discount) |

**Note:** `created_by` is set automatically to the logged-in user.

**Success (201):** Created announcement object (same shape as list/detail).

### PATCH – Update announcement

**URL:** `{{baseurl}}/alertsapi/announcements/<id>/`  
**Method:** `PATCH`  
**Headers:** `Content-Type: application/json`

**Body (example):**

```json
{
  "announcement": "Updated announcement text.",
  "percentage": 20
}
```

### DELETE – Delete announcement

**URL:** `{{baseurl}}/alertsapi/announcements/<id>/`  
**Method:** `DELETE`

**Success (204):** No content.

---

## Summary

| Resource | List | Retrieve | Create | Update | Delete |
|----------|------|----------|--------|--------|--------|
| Alert types | `GET /alertsapi/alert-types/` | `GET /alertsapi/alert-types/<id>/` | — | — | — |
| Alerts | `GET /alertsapi/alerts/` | `GET /alertsapi/alerts/<id>/` | `POST /alertsapi/alerts/` | `PUT/PATCH /alertsapi/alerts/<id>/` | `DELETE /alertsapi/alerts/<id>/` |
| Announcement types | `GET /alertsapi/announcement-types/` | `GET /alertsapi/announcement-types/<id>/` | — | — | — |
| Announcements | `GET /alertsapi/announcements/` | `GET /alertsapi/announcements/<id>/` | `POST /alertsapi/announcements/` | `PUT/PATCH /alertsapi/announcements/<id>/` | `DELETE /alertsapi/announcements/<id>/` |
