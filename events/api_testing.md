# Events APIs – Testing reference

Base prefix: `{{baseurl}}/eventsapi/`

Use this file to document all executable APIs exposed by the `events` app (meetings, holidays, tours, birthday counter, etc.).

---

## 1. Routers / viewsets

Most events endpoints are registered via DRF routers in `events/urls.py` (e.g. `MeetingViewSet`, `HolidayViewSet`, etc.).

> For each viewset in `events/views.py`, add:
> - Base URL under `/eventsapi/`
> - List / retrieve / create / update / delete examples
> - Any custom actions (e.g. cron endpoints on viewsets)

---

## 1a. Meeting push (`MeetingViewSet`)

**Base URL:** `{{baseurl}}/eventsapi/meetingpush/`

| Action   | Method | URL |
|----------|--------|-----|
| List     | GET    | `/eventsapi/meetingpush/` |
| Create   | POST   | `/eventsapi/meetingpush/` |
| Retrieve | GET    | `/eventsapi/meetingpush/<id>/` |
| Update   | PUT/PATCH | `/eventsapi/meetingpush/<id>/` |
| Delete   | DELETE | `/eventsapi/meetingpush/<id>/` |
| Cron     | GET    | `/eventsapi/meetingpush/cron/delete-previous-days/` (header `X-CRON-KEY`) |

**GET list / retrieve — response shape**

Meetings return **names only** for foreign keys — **no `product_id` or `meeting_room_id`** (or any FK id) in the JSON.

Example item:

```json
{
  "id": 1,
  "product_name": "Product A",
  "room_name": "Conference Room 1",
  "meeting_type": "group",
  "time": 30,
  "is_active": true,
  "created_at": "09/03/2025 14:30:00"
}
```

- `product_name` — full `project.Product.name` (or `null` if no product).
- `room_name` — full `Room.name` (or `null` if no room).

**POST / PATCH / PUT — body (write by name)**

Use **product name** and **room name** strings (not ids):

```json
{
  "product": "Product A",
  "meeting_room": "Conference Room 1",
  "meeting_type": "group",
  "time": 30,
  "is_active": true
}
```

- `product` — optional; must match an existing `Product.name` if provided.
- `meeting_room` — must match an existing `Room.name` when provided (optional if your flow allows unassigned room; model allows null).
- `meeting_type` — `individual` | `group`.
- `time` — duration in minutes (integer).

After create/update, the same GET shape applies (names only, no FK ids).

**WebSocket — product channel notification**

When a meeting has a **product** set, the backend can broadcast on the **product-named channel** (`notifications_product_<ProductName>`, spaces → underscores). Payload uses `category: "Meeting_push"` and **`title`** / **`extra.action`** as:

| Situation | `title` / `extra.action` |
|-----------|---------------------------|
| New meeting saved | **Created** |
| **time** (duration) changed | **reschedule** |
| Other attributes changed (room, type, etc.) without time change | **updated** |
| Meeting deleted | **abandoned** |

**No broadcast** when the only change is toggling **`is_active`** (no WebSocket send). If the meeting has no product, no product-channel broadcast is sent.

`extra` includes `product_name`, `room_name`, `meeting_type`, `time_minutes`, `is_active` where applicable.

---

## 2. Birthday counter

Standalone endpoints (non-router) from `events/urls.py`:

- `POST {{baseurl}}/eventsapi/events/birthdaycounter/` – bulk increment birthday counters:
  - Body: `{"users": ["username1", "username2", ...]}`
- `GET  {{baseurl}}/eventsapi/events/birthdaycounter/<username>/` – get birthday counter for a single user.

> Add detailed request/response samples and error cases here.

