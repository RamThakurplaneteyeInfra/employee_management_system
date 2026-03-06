# Notifications APIs – Testing reference

Base prefix: `{{baseurl}}/notifications/`

Use this file to document all executable notification-related APIs (list, mark read, cron cleanup, websocket info, etc.).

---

## 1. Core notification APIs

From `notifications/urls.py`:

- `GET {{baseurl}}/notifications/today/` – fetch today's notifications for the logged-in user.
- `GET {{baseurl}}/notifications/types/` – list available notification types.
- `POST {{baseurl}}/notifications/read/<pk>/` – mark a notification as read.

> Add request/response examples for each of the above.

---

## 2. Cron cleanup APIs (permissionless)

- `GET {{baseurl}}/notifications/cron/delete-seen-older-than-day/`
- `GET {{baseurl}}/notifications/cron/delete-unseen-older-than-week/`

These are designed to be called by the external cron job and do not require auth.

> Document expected success responses and how to configure the cron caller.

