# Messaging APIs – Testing reference (Postman)

**Base URL:** `{{baseurl}}/messaging/`

> **React integration:** For a detailed, in-detail prompt to integrate these APIs and the chat WebSocket in a React client (order of calls, WebSocket triggers, state handling), see **`Messaging/REACT_INTEGRATION_PROMPT.md`**.
<!--   
**Auth:** All endpoints require a **logged-in user** (session/cookie).  
**Note:** Call APIs (1:1 and group calls) live under the same `/messaging/` prefix; see **Calling/api_testing.md** for call endpoints.

--- -->

## 1. Group management

### Create group
<!-- 
| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/createGroup/` |

**Body (JSON):**
```json
{
  "group_name": "My Team",
  "description": "Optional description",
  "participants": ["user1", "user2"]
}
```

| Key         | Type  | Required | Description |
|-------------|-------|----------|-------------|
| group_name  | string| Yes      | Name of the group |
| description | string| No       | Optional description |
| participants| array | Yes      | List of usernames to add (at least one). Keys can be indices, e.g. `{"0": "user1", "1": "user2"}` or array `["user1", "user2"]` |

**Success (201):** `{ "Messsage": "Group created successfully" }`  
**Errors:** 403 if user cannot create groups; 406 if participants missing/invalid.

--- -->

### Show created groups

<!-- | Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/showCreatedGroups/` |

No body. Returns groups created by the logged-in user.

**Success (200):** Array of `{ "group_id": "...", "total_participant": N, "name": "...", "description": "...", "created_at": "dd/mm/yyyy, HH:MM:SS" }` (IST).

--- -->

### Show group members

<!-- | Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/showGroupMembers/<group_id>/` |

Replace `<group_id>` with the group’s `group_id` (e.g. `G-xxx`).

**Success (200):** Array of objects with `participant` (username), `participant_name` (Profile name), `groupchat`.

--- -->

### Add user to group

<!-- | Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/addUser/<group_id>/` |

**Body (JSON):**
```json
{
  "participant": "username_to_add"
}
```

**Success (200):** Group member list or success response. **302** if user already in group.

--- -->

### Delete user from group

<!-- | Method | URL |
|--------|-----|
| DELETE | `{{baseurl}}/messaging/deleteUser/<group_id>/<user_id>/` |

`<user_id>` is the username to remove.

**Success (202):** User removed. **403** if not allowed.

--- -->

### Delete group

<!-- | Method | URL |
|--------|-----|
| DELETE | `{{baseurl}}/messaging/deleteGroup/<group_id>/` |

**Success (202):** `{ "message": "group deleted successfully" }`  
**403** if user is not allowed to delete the group.

--- -->

## 2. Chats and messages

### Start or get individual chat

<!-- | Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/startChat/` |

**Body (JSON):**
```json
{
  "participant": "other_username"
}
```

**Success (200):**  
- If chat already exists: `{ "chat_id": "...", "participant": "<Full Name>", "messages": {} }`  
- If new: returns message list for the new chat (same structure as getMessages).

--- -->

### Post message (group or individual)

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/postMessages/<chat_id>/` |

`<chat_id>` is either a group id (e.g. `G-xxx`) or an individual `chat_id`.  
Send at least one of: **Message** (text) or **attachment_ids** (ids from uploadFile/addLink).

<!-- **Body (JSON) – message only:**
```json
{
  "Message": "Hello everyone."
}
```

**Body – message with attachments:** (attach first via uploadFile/addLink, then pass their ids)
```json
{
  "Message": "See the file.",
  "attachment_ids": [1, 2]
}
```

**Body – attachments only (standalone in chat):**
```json
{
  "attachment_ids": [1]
}
```

| Key            | Type  | Required | Description |
|----------------|-------|----------|-------------|
| Message        | string| No*      | Text content (*required if no attachment_ids) |
| attachment_ids | array | No*      | IDs of MessageAttachment from uploadFile/addLink (*required if no Message) |

**Success (201):** `{ "message": "Message sent successfully" }`  
**Errors:** 400 invalid chat/group id; 204 if neither Message nor attachment_ids provided.

--- -->

### Get messages

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/getMessages/<chat_id>/` |

**Success (200):** Response shape depends on implementation; typically list of messages with `message`, `attachments`, `quote` (if any), sender info, timestamps in IST.

---

### Load groups and chats (inbox)

<!-- | Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/loadChats/` |

No body. Returns groups and individual chats for the logged-in user, ordered by last activity, with unseen counts.

**Success (200):**
```json
{
  "Group_info": [
    {
      "group_id": "...",
      "group_name": "...",
      "description": "...",
      "total_participant": N,
      "last_message_at": "dd/mm/yy HH:MM:SS",
      "unseen_count": 0
    }
  ],
  "chats_info": [
    {
      "chat_id": "...",
      "with": "<Other user full name>",
      "last_message_at": "dd/mm/yy HH:MM:SS",
      "unseen_count": 0
    }
  ]
}
```
All times in IST.

---

## 3. Attachments

### Upload file

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/uploadFile/` |

**Content-Type:** `multipart/form-data`  
**Field name:** `file`

**Success (201):**
```json
{
  "id": 1,
  "s3_key": "...",
  "file_name": "doc.pdf",
  "content_type": "application/pdf",
  "file_size": 12345,
  "url": "<presigned or public URL>"
}
```
Use `id` in `attachment_ids` when posting a message to link this file to the message (or send attachment only to post as standalone).

---

### Add link

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/addLink/` |

**Body (JSON):**
```json
{
  "url": "https://example.com/page",
  "title": "Optional link title"
}
```
`title` can also be sent as `link_title`.

**Success (201):** `{ "id": 2, "url": "...", "title": "..." }`  
Use `id` in `attachment_ids` when posting a message.

--- -->

### Delete attachment

<!-- | Method | URL |
|--------|-----|
| DELETE | `{{baseurl}}/messaging/attachments/<attachment_id>/` |

Only the uploader can delete; only **unlinked** attachments (not yet sent in a message) can be deleted.

**Success (200):** `{ "message": "Attachment deleted" }`  
**Errors:** 403 not allowed; 404 not found; 400 if attachment already sent.

--- -->

### Get attachment URL

<!-- | Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/files/<attachment_id>/url/` |

Returns a URL to view/download the file or link. User must have access (member of group/chat or owner of unlinked attachment).

**Success (200):** `{ "url": "...", "file_name": "...", "type": "file" }` or `"type": "link"` for links.

--- -->

## 4. Calling APIs (under same prefix)

<!-- All call-related endpoints (callableUsers, initiateCall, acceptCall, declineCall, endCall, screenShare, stopScreenShare, missedCallsCount, resetMissedCallsCount, pendingCalls, activeCalls, endAllMyCalls, initiateGroupCall, joinGroupCall, leaveGroupCall, endGroupCall, activeGroupCalls, callHistory) are documented in **Calling/api_testing.md**.  
Base path for those: `{{baseurl}}/messaging/` (e.g. `{{baseurl}}/messaging/initiateCall/`). -->

---

## 5. Real-Time Chat WebSocket

**URL:** `ws://<host>/ws/chat/` (dev) or `wss://<host>/ws/chat/` (prod).  
**Auth:** Session-based (same as `/ws/notifications/` and `/ws/calls/`). The browser must send the session cookie with the WebSocket handshake (same origin, or cross-origin with `SameSite=None; Secure`). If the user is not logged in, the connection is rejected (closed with code 4001).

### Client → Server (outgoing)

| type           | payload | purpose |
|----------------|--------|--------|
| subscribe      | `{ "chat_id": "C12345" }` or `"G12345"` | Subscribe to updates for this chat (DM or group). Multiple subscriptions per connection. |
| unsubscribe    | `{ "chat_id": "C12345" }` | Stop receiving updates for this chat. |
| typing_start   | `{ "chat_id": "C12345" }` | User started typing. |
| typing_stop    | `{ "chat_id": "C12345" }` | User stopped typing. |
| mark_seen      | `{ "chat_id": "C12345" }` or `{ "chat_id": "C12345", "user_id": "logged_in_username" }` | `{ "chat_id": "C12345", "message_ids": [101, 102] }` or `{ "last_message_id": 103 }` or omit both for “all seen” | Mark entire chat as seen for the logged-in user (chat_id and optional user_id only). Persisted; server replies with unseen_count_updated (0). |

### Server → Client (incoming)

| type           | payload |
|----------------|--------|
| new_message    | `chat_id`, `message` (id, sender, sender_name, message, date, time, attachments, created_at) — when a message is created via POST postMessages. |
| chat_updated   | `chat_id`, `last_message_at`, `last_message_preview`, `unseen_count` — so chat list can refresh. |
| messages_seen  | `chat_id`, `seen_by`, `seen_by_name`, `message_ids` and/or `last_seen_message_id`, `seen_at`. |
| user_typing    | `chat_id`, `user_id`, `user_name`, `is_typing` (true/false). Not sent to the user who is typing. Typing auto-expires after 8s if no typing_stop. |
| unseen_count_updated | `chat_id`, `unseen_count` — sent to the user it applies to (`for_user`). After mark_seen the client gets 0; when a new message is posted, non-senders get their updated count (group: GroupMembers.unseenmessages; DM: count of unseen IndividualMessages). |
| error          | `message` — e.g. “Not a participant”. |

**mark_seen payload:** send only `chat_id` (and optionally `user_id` matching the logged-in user). Do not send `message_ids` or `last_message_id`; the server marks the entire chat as seen.

Chat IDs are the same as in `loadChats` and `getMessages` (e.g. `C12345678` for DM, `G12345` for group). Only participants can subscribe or mark_seen; non-participants get an error.

---

## 6. Mark as read (REST)

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/markSeen/<chat_id>/` |

**Body (JSON):** either `{ "message_ids": [101, 102, 103] }` or `{ "last_message_id": 103 }`, or `{}` to mark all messages in the chat as seen.

Same permission as WebSocket mark_seen (user must be a participant). Read state is persisted and broadcast to `chat_<chat_id>` so WebSocket clients receive `messages_seen`.

**Success (200):** `{ "status": "ok" }`  
**Error (403):** `{ "message": "Not a participant" }` or similar.

**GET getMessages** response for individual (DM) messages now includes a `seen` boolean per message where applicable.

---

## 7. Frontend client: recommended flow and calling order

Use this order so the chat list, messages, and unseen counts stay in sync with the backend and WebSocket.

---

### Flow A: App load (chat list + real-time connection)

| Step | Action | Payload / Request | Response (API or WebSocket) |
|------|--------|-------------------|-----------------------------|
| 1 | **Connect WebSocket** | Open `ws://<host>/ws/chat/` (session cookie sent automatically) | Connection accepted, or closed with 4001 if not logged in |
| 2 | **Load chat list** | `GET {{baseurl}}/messaging/loadChats/` | `200` → `{ "Group_info": [...], "chats_info": [...] }` with `unseen_count` per group/chat |

**Result:** User sees inbox with groups and DMs; unseen counts match server. WebSocket is open for real-time events.

---

### Flow B: User opens a chat (read messages + mark as seen)

| Step | Action | Payload / Request | Response (API or WebSocket) |
|------|--------|-------------------|-----------------------------|
| 1 | **Subscribe to chat** | WS send: `{ "type": "subscribe", "chat_id": "C12345" }` or `"G12345"` | No reply; from now on you receive events for this chat |
| 2 | **Fetch messages** | `GET {{baseurl}}/messaging/getMessages/<chat_id>/` | `200` → array of messages (id, sender, message, date, time, attachments, seen for DM) |
| 3 | **Mark chat as seen (implicit)** | WS send: `{ "type": "mark_seen", "chat_id": "C12345" }` or with `"user_id": "<logged_in_username>"` | WS receive: `{ "type": "unseen_count_updated", "chat_id": "C12345", "unseen_count": 0 }`; other participants may receive `messages_seen` |

**Result:** Messages are shown; DB is updated (GroupMembers or IndividualMessages); client gets `unseen_count: 0` so the chat list badge can update without calling loadChats again.

---

### Flow C: User sends a new message

| Step | Action | Payload / Request | Response (API or WebSocket) |
|------|--------|-------------------|-----------------------------|
| 1 | **Post message** | `POST {{baseurl}}/messaging/postMessages/<chat_id>/` body: `{ "Message": "Hello" }` or `{ "attachment_ids": [1] }` | `201` → `{ "message": "Message sent successfully" }` |
| 2 | *(Server-side)* | — | All subscribers (including sender) receive WS: `{ "type": "new_message", "chat_id": "...", "message": { "id", "sender", "sender_name", "message", "date", "time", "attachments", "created_at" } }` |
| 3 | *(Server-side)* | — | All subscribers receive WS: `{ "type": "chat_updated", "chat_id": "...", "last_message_at": "...", "last_message_preview": "...", "unseen_count": 0 }` |
| 4 | *(Server-side)* | — | **Non-senders only** receive WS: `{ "type": "unseen_count_updated", "chat_id": "...", "unseen_count": N }` (N = 1 for DM, or incremented for group) |

**Result:** Message appears in all clients; chat list can refresh from `chat_updated`; recipients get updated unseen count for their list.

---

### Flow D: Typing indicator

| Step | Action | Payload / Request | Response (API or WebSocket) |
|------|--------|-------------------|-----------------------------|
| 1 | User starts typing | WS send: `{ "type": "typing_start", "chat_id": "C12345" }` | — |
| 2 | *(Server-side)* | — | **Other participants** receive: `{ "type": "user_typing", "chat_id": "C12345", "user_id": "...", "user_name": "...", "is_typing": true }` |
| 3 | User stops typing | WS send: `{ "type": "typing_stop", "chat_id": "C12345" }` | Others receive: `{ "type": "user_typing", ..., "is_typing": false }` (or auto-expires after ~8s if no typing_stop) |

---

### Flow E: User leaves chat screen

| Step | Action | Payload / Request | Response |
|------|--------|-------------------|----------|
| 1 | Unsubscribe | WS send: `{ "type": "unsubscribe", "chat_id": "C12345" }` | No reply; you stop receiving events for this chat |

---

### Summary: minimal order for “open chat” experience

1. **Before showing any chat:** Connect WebSocket → (optional) loadChats.  
2. **When user opens a chat:** Subscribe (WS) → getMessages (API) → mark_seen (WS).  
3. **When user sends a message:** postMessages (API); new_message + chat_updated + unseen_count_updated come over WS.  
4. **When user closes chat:** Unsubscribe (WS).

Use the **same `chat_id`** (e.g. `C12345678` or `G12345`) for getMessages, postMessages, markSeen, and WebSocket subscribe/mark_seen/typing.

---

### Client implementation guide (WebSocket triggers and handlers)

Short, step-by-step implementation so the client sends the right payloads at the right time and reacts correctly to each WebSocket event.

---

#### 1. Connection and chat list

| Trigger | Action | Payload / Request | What to do next |
|--------|--------|-------------------|------------------|
| App loads / user logs in | Open WebSocket | `new WebSocket('ws://<host>/ws/chat/')` (cookie sent automatically) | On `open`: optionally call `GET /messaging/loadChats/` and render inbox with `Group_info` and `chats_info` (use `unseen_count` for badges). |
| — | — | If connection closes with code 4001 | User is not authenticated; redirect to login or show error. |

---

#### 2. Opening a chat (subscribe → fetch → mark seen)

| Trigger | Action | Payload / Request | What to do next |
|--------|--------|-------------------|------------------|
| User taps/clicks a chat (DM or group) | **1. Subscribe** (send immediately) | `ws.send(JSON.stringify({ "type": "subscribe", "chat_id": "<chat_id>" }))` | Then call REST. |
| Right after subscribe | **2. Fetch messages** | `GET {{baseurl}}/messaging/getMessages/<chat_id>/` | On 200: render message list (id, sender, message, date, time, attachments, seen). |
| As soon as getMessages succeeds | **3. Mark as seen** (implicit) | `ws.send(JSON.stringify({ "type": "mark_seen", "chat_id": "<chat_id>" }))` or add `"user_id": "<logged_in_username>"` | Wait for WS reply to update badge. |

**Example payloads (client sends):**
```json
{"type": "subscribe", "chat_id": "C12345678"}
```
```json
{"type": "mark_seen", "chat_id": "C12345678"}
```
```json
{"type": "mark_seen", "chat_id": "G12345", "user_id": "alice"}
```

---

#### 3. WebSocket message handler (what to do when you receive an event)

Handle `message.data` as JSON and branch on `type`:

| Event `type` | When it arrives | Client action | Example payload (client receives) |
|--------------|------------------|---------------|-----------------------------------|
| **unseen_count_updated** | After you sent `mark_seen`, or when someone else posted in a chat you’re in | Update local state for this `chat_id`: set `unseen_count` (e.g. for chat list badge). If `unseen_count === 0`, clear badge. | `{"type": "unseen_count_updated", "chat_id": "C12345678", "unseen_count": 0}` |
| **new_message** | Someone (including you) posted in a chat you’re subscribed to | Append `event.message` to the message list for `event.chat_id`. If that chat is open, render it; optionally scroll to bottom and play sound if sender is not self. | `{"type": "new_message", "chat_id": "C12345678", "message": {"id": 101, "sender": "bob", "sender_name": "Bob", "message": "Hi", "date": "09/03/26", "time": "14:30:00", "attachments": [], "created_at": "2026-03-09T14:30:00Z"}}` |
| **chat_updated** | A message was sent in the chat | Update chat list row for `event.chat_id`: set `last_message_at`, `last_message_preview`; use `unseen_count` from event if you don’t rely on `unseen_count_updated` for this. | `{"type": "chat_updated", "chat_id": "C12345678", "last_message_at": "2026-03-09T14:30:00Z", "last_message_preview": "Hi", "unseen_count": 0}` |
| **messages_seen** | Another participant marked messages as read | Optional: show “Seen by …” or read receipts in the message list for `event.chat_id` using `seen_by`, `seen_by_name`, `message_ids` / `last_seen_message_id`, `seen_at`. | — |
| **user_typing** | Another participant started or stopped typing | If `event.is_typing === true`, show “`event.user_name` is typing…” for `event.chat_id`; if `false`, hide it. Typing auto-expires ~8s if no `typing_stop`. | `{"type": "user_typing", "chat_id": "C12345678", "user_id": "bob", "user_name": "Bob", "is_typing": true}` |
| **error** | Invalid action (e.g. not a participant) | Show `event.message` to the user (toast or inline). | `{"type": "error", "message": "Not a participant"}` |

Recipients (non-senders) also receive **unseen_count_updated** when a new message is posted, so the chat list badge updates in real time:
```json
{"type": "unseen_count_updated", "chat_id": "C12345678", "unseen_count": 1}
```

---

#### 4. Sending a message

| Trigger | Action | Payload / Request | What to do next |
|--------|--------|-------------------|------------------|
| User sends a message (or attachment) | Call REST only | `POST {{baseurl}}/messaging/postMessages/<chat_id>/` body: `{ "Message": "Hello" }` or `{ "attachment_ids": [1] }` | On 201: you will receive **new_message** and **chat_updated** over WebSocket for this chat; optionally show an optimistic message and replace with the one from **new_message** when it arrives. |

No need to send anything over WebSocket to “notify” the server that you sent a message; the server broadcasts after the REST call.

---

#### 5. Typing indicators

| Trigger | Action | Payload (client sends) | What happens |
|--------|--------|------------------------|--------------|
| User focuses input and starts typing | Send once (debounce ~300–500 ms) | `{"type": "typing_start", "chat_id": "<chat_id>"}` | Other participants receive **user_typing** with `is_typing: true`. |
| User stops typing (blur or idle ~2–3 s) | Send once | `{"type": "typing_stop", "chat_id": "<chat_id>"}` | Others receive **user_typing** with `is_typing: false`. If you don’t send this, server clears typing after ~8 s. |

**Example:** `{"type": "typing_start", "chat_id": "C12345678"}`

---

#### 6. Leaving the chat screen

| Trigger | Action | Payload (client sends) |
|--------|--------|------------------------|
| User navigates away from the chat (e.g. back to list) | Unsubscribe so you stop receiving events for this chat | `{"type": "unsubscribe", "chat_id": "<chat_id>"}` |

---

#### Execution order summary

1. **On app load:** Connect WS → (optional) loadChats.
2. **On open chat:** Send **subscribe** → GET getMessages → send **mark_seen**; handle **unseen_count_updated** to set badge to 0.
3. **On new message (received):** Handle **new_message** (append to list), **chat_updated** (update list row), **unseen_count_updated** (update badge for recipients).
4. **On send message:** POST postMessages only; rely on **new_message** / **chat_updated** from WS to update UI.
5. **On leave chat:** Send **unsubscribe**.

---

## Quick reference

| Purpose           | Method | URL |
|-------------------|--------|-----|
| Create group      | POST   | `/messaging/createGroup/` |
| Show created groups | GET  | `/messaging/showCreatedGroups/` |
| Group members     | GET    | `/messaging/showGroupMembers/<group_id>/` |
| Add user to group | POST   | `/messaging/addUser/<group_id>/` |
| Delete user from group | DELETE | `/messaging/deleteUser/<group_id>/<user_id>/` |
| Delete group      | DELETE | `/messaging/deleteGroup/<group_id>/` |
| Start chat        | POST   | `/messaging/startChat/` |
| Post message      | POST   | `/messaging/postMessages/<chat_id>/` |
| Get messages      | GET    | `/messaging/getMessages/<chat_id>/` |
| Mark as read      | POST   | `/messaging/markSeen/<chat_id>/` |
| Load chats        | GET    | `/messaging/loadChats/` |
| Upload file       | POST   | `/messaging/uploadFile/` |
| Add link          | POST   | `/messaging/addLink/` |
| Delete attachment | DELETE | `/messaging/attachments/<attachment_id>/` |
| Get attachment URL| GET    | `/messaging/files/<attachment_id>/url/` |
| Chat WebSocket    | WS     | `/ws/chat/` (session cookie) |
