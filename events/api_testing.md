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

## 2. Birthday counter

Standalone endpoints (non-router) from `events/urls.py`:

- `POST {{baseurl}}/eventsapi/events/birthdaycounter/` – bulk increment birthday counters:
  - Body: `{"users": ["username1", "username2", ...]}`
- `GET  {{baseurl}}/eventsapi/events/birthdaycounter/<username>/` – get birthday counter for a single user.

> Add detailed request/response samples and error cases here.

