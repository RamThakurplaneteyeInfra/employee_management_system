# Calling APIs – Testing reference

Base prefix: `{{baseurl}}/messaging/` (calling endpoints are included in `Messaging/urls.py`).

Use this file to document all executable voice/video call related APIs.

---

## 1. One-to-one calls

- `GET/POST {{baseurl}}/messaging/callableUsers/`
- `POST     {{baseurl}}/messaging/initiateCall/`
- `POST     {{baseurl}}/messaging/acceptCall/`
- `POST     {{baseurl}}/messaging/declineCall/`
- `POST     {{baseurl}}/messaging/endCall/`
- `GET      {{baseurl}}/messaging/pendingCalls/`
- `GET      {{baseurl}}/messaging/activeCalls/`
- `POST     {{baseurl}}/messaging/endAllMyCalls/`

> For each endpoint above, add the exact HTTP method, request body, and sample response.

---

## 2. Group calls

- `POST {{baseurl}}/messaging/initiateGroupCall/`
- `POST {{baseurl}}/messaging/joinGroupCall/`
- `POST {{baseurl}}/messaging/leaveGroupCall/`
- `POST {{baseurl}}/messaging/endGroupCall/`
- `GET  {{baseurl}}/messaging/activeGroupCalls/`

> Document how to start/join/leave/end group calls and how to interpret the active calls response.

