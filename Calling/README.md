# Calling app – Audio/Video calls

Audio and video calling (1:1 and group) via HTTP APIs and WebSocket signaling.

## Base URL

- **HTTP APIs:** Under `/messaging/` (included via `Messaging.urls`).  
  Example: `POST /messaging/initiateCall/`, `GET /messaging/pendingCalls/`, etc.
- **WebSocket:** `wss://<host>/ws/calls/` (ASGI; use the same host as the API in production so session cookies are sent).
- **Auth:** Connections are **rejected (403/close 4001)** if the user is not authenticated—same rules as `/ws/notifications/`. Open this socket **after login** using the same origin (or cross-origin with `SameSite=None; Secure` on the session cookie) so the session cookie is sent. Close the socket on **logout** (same as notifications).

## Deployment

1. **INSTALLED_APPS:** `Calling` is in `ems.settings.INSTALLED_APPS`.
2. **Database:** Models use schema `Messaging` (`db_table = 'Messaging"."Calls'` etc.). Ensure the `Messaging` schema exists (e.g. created by Messaging app migrations).
3. **Migrations:** Run `python manage.py migrate Calling` so `Call`, `GroupCall`, and `GroupCallParticipant` tables exist in the `Messaging` schema.
4. **ASGI:** Use Daphne (or another ASGI server) so WebSockets work; the app is configured in `ems.asgi`.
5. **Redis:** Channels layer uses Redis; required for WebSocket group messaging and call signaling.

## Dependencies

Already in `requirements.txt`: `channels`, `channels-redis`, `daphne`. No extra install needed.
