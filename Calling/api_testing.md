# Calling APIs – Testing reference (Postman)

**Base URL:** `{{baseurl}}/messaging/` (Calling routes are included under Messaging).

**Auth:** All endpoints require a **logged-in user** (session/cookie).

**Models:** `Call` (1:1) and `GroupCall` both have:
- **status:** Call: `pending`, `accepted`, `declined`, `ended`, `missed`. GroupCall: `active`, `ended`, `missed`.
- **is_screen_shared:** boolean (default `false`). Set to `true` when a participant shares screen via PATCH screenShare/.

---

## 1. Get callable users

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/callableUsers/` |

No body. Returns list of users (excluding self) with `username`, `name` (Profile full name), and `is_busy` (true if in an active 1:1 call).

---

## 2. Initiate call (1:1)

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/initiateCall/` |

**Body (JSON):**
```json
{
  "user_id": "receiver_username",
  "call_type": "audio"
}
```
`call_type`: `"audio"` or `"video"`.

**Success (201):** `{ "success": true, "call_id": <int>, "call_type": "...", "sender": "...", "receiver": "..." }`

---

## 3. Accept call

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/acceptCall/` |

**Body (JSON):**
```json
{
  "call_id": 123
}
```

**Success (200):** `{ "success": true, "call_id": <int> }`

---

## 4. Decline call

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/declineCall/` |

**Body (JSON):**
```json
{
  "call_id": 123
}
```

**Success (200):** `{ "success": true, "call_id": <int> }`

---

## 5. End call (1:1)

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/endCall/` |

**Body (JSON):**
```json
{
  "call_id": 123
}
```

**Success (200):** `{ "success": true, "call_id": <int>, "sender": "...", "receiver": "..." }`  
Other participant is notified via WebSocket.

---

## 6. Screen share (1:1 or group)

| Method | URL |
|--------|-----|
| PATCH  | `{{baseurl}}/messaging/screenShare/` |

**Body (JSON):** Send **either** `call_id` (1:1) **or** `group_call_id` (group), not both.

1:1 example:
```json
{
  "call_id": 123
}
```

Group example:
```json
{
  "group_call_id": 456
}
```

**Success (200):** `{ "success": true, "is_screen_shared": true, "shared_by_name": "<Full Name from Profile>" }`  
Other participants are notified via WebSocket (`screen_shared` event).

---

## 7. Pending calls (incoming, not yet answered)

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/pendingCalls/` |

No body. Returns list of calls where current user is **receiver** and status is **pending**.

**Response (200):** Array of objects:
- `call_id`, `sender`, `receiver`, `call_type`, `status`, `is_screen_shared`, `timestamp` (IST with seconds).

---

## 8. Active calls (1:1)

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/activeCalls/` |

No body. Returns list of calls where current user is sender or receiver and status is **pending** or **accepted**.

**Response (200):** Array of objects:
- `call_id`, `sender`, `receiver`, `call_type`, `status`, `is_screen_shared`, `timestamp` (IST with seconds).

---

## 9. End all my calls

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/endAllMyCalls/` |

No body (or empty JSON). Ends all active 1:1 calls (pending/accepted) for the current user.

**Success (200):** `{ "success": true, "ended_count": <int>, "message": "Ended N call(s)." }`

---

## 10. Initiate group call

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/initiateGroupCall/` |

**Body (JSON):**
```json
{
  "call_type": "video",
  "invitees": ["user1", "user2"]
}
```
`call_type`: `"audio"` or `"video"`. `invitees`: array of usernames.

**Success (201):** `{ "success": true, "call_id": <int> }`

---

## 11. Join group call

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/joinGroupCall/` |

**Body (JSON):**
```json
{
  "call_id": 456
}
```

**Success (200):** `{ "success": true, "call_id": <int> }`

---

## 12. Leave group call

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/leaveGroupCall/` |

**Body (JSON):**
```json
{
  "call_id": 456
}
```

**Success (200):** `{ "success": true, "call_id": <int> }`

---

## 13. End group call

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/endGroupCall/` |

**Body (JSON):**
```json
{
  "call_id": 456
}
```

**Success (200):** `{ "success": true, "call_id": <int> }`

---

## 14. Active group calls

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/activeGroupCalls/` |

No body. Returns list of **active** group calls where current user is creator or participant.

**Response (200):** Array of objects:
- `call_id`, `creator`, `call_type`, `status`, `is_screen_shared`, `created_at` (IST with seconds), `participants_joined`, `participants_invited` (arrays of usernames).

---

## 15. Call history

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/callHistory/` |

No body. Returns combined history of 1:1 and group calls for the current user, sorted by time (newest first).

**Response (200):** Array of items. Each item has:
- **Individual:** `call_kind`: `"individual"`, `id`, `sender`, `receiver`, `call_type`, `status`, `is_screen_shared`, `timestamp`, `initiator`, `initiator_name`, `participant` (list of names).
- **Group:** `call_kind`: `"group"`, `id`, `creator`, `call_type`, `status`, `is_screen_shared`, `created_at`, `initiator`, `initiator_name`, `participant` (list of names).

**Call status values:** `pending`, `accepted`, `declined`, `ended`, `missed`.  
**GroupCall status values:** `active`, `ended`, `missed`.

---

## Quick reference

| Purpose           | Method | URL |
|-------------------|--------|-----|
| Callable users    | GET    | `/messaging/callableUsers/` |
| Initiate 1:1 call | POST   | `/messaging/initiateCall/` |
| Accept call       | POST   | `/messaging/acceptCall/` |
| Decline call      | POST   | `/messaging/declineCall/` |
| End 1:1 call      | POST   | `/messaging/endCall/` |
| Screen share      | PATCH  | `/messaging/screenShare/` |
| Pending calls     | GET    | `/messaging/pendingCalls/` |
| Active 1:1 calls  | GET    | `/messaging/activeCalls/` |
| End all my calls  | POST   | `/messaging/endAllMyCalls/` |
| Initiate group call | POST | `/messaging/initiateGroupCall/` |
| Join group call   | POST   | `/messaging/joinGroupCall/` |
| Leave group call  | POST   | `/messaging/leaveGroupCall/` |
| End group call    | POST   | `/messaging/endGroupCall/` |
| Active group calls| GET    | `/messaging/activeGroupCalls/` |
| Call history      | GET    | `/messaging/callHistory/` |
