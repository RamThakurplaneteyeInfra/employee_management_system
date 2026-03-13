# React client integration prompt – Messaging backend

Use this prompt when implementing or integrating the **Messaging** feature in your React app. The backend API and WebSocket contract are fully described in **`Messaging/api_testing.md`** in this repo; treat that file as the single source of truth for URLs, payloads, and response shapes. This document translates that into React-oriented steps, triggers, and implementation notes.

---

## 1. Reference and environment

- **Backend API spec:** `Messaging/api_testing.md` (same repo).
- **Base URL:** Use an env variable, e.g. `VITE_API_BASE` or `REACT_APP_API_BASE`, so that:
  - REST base = `https://<your-api-host>` (e.g. `https://api.example.com`).
  - Messaging REST paths are under `/messaging/` (e.g. `GET /messaging/loadChats/`).
- **WebSocket URL:** `ws://<host>/ws/chat/` in development, `wss://<host>/ws/chat/` in production. Use the same host (and port, if any) as the REST API so the session cookie is sent with the WebSocket handshake.
- **Auth:** All REST calls and the WebSocket use **session (cookie) authentication**. Send credentials so the session cookie is attached:
  - `fetch`: use `credentials: 'include'`.
  - `axios`: use `withCredentials: true`.
  - WebSocket: the browser sends the cookie to the same origin automatically; if the React app is on a different origin, use the same host for the WS URL and ensure the backend allows that origin and uses `SameSite`/CORS correctly (see api_testing.md).

---

## 2. REST endpoints to integrate (from api_testing.md)

Call these in the order and at the times described below. Exact request/response shapes are in **Messaging/api_testing.md**.

| Purpose | Method | Path | When to call (React trigger) |
|--------|--------|------|------------------------------|
| Load chat list (inbox) | GET | `/messaging/loadChats/` | After WebSocket connects (e.g. on app load or after login). |
| Start or get DM | POST | `/messaging/startChat/` | When user starts a new 1:1 chat (body: `{ "participant": "other_username" }`). |
| Get messages | GET | `/messaging/getMessages/<chat_id>/` | When user opens a chat, **after** sending WebSocket `subscribe` (see below). |
| Post message | POST | `/messaging/postMessages/<chat_id>/` | When user sends a message or attachment (body: `{ "Message": "..." }` and/or `{ "attachment_ids": [1,2] }`). |
| Mark as read (optional REST) | POST | `/messaging/markSeen/<chat_id>/` | Optional; the **WebSocket mark_seen** flow is preferred for “implicit” mark-as-seen after getMessages (see Section 4). |
| Upload file | POST | `/messaging/uploadFile/` | Before posting a message with a file: multipart form with `file`; use returned `id` in `attachment_ids`. |
| Add link | POST | `/messaging/addLink/` | Before posting a message with a link (body: `{ "url", "title" }`); use returned `id` in `attachment_ids`. |

Use the **same `chat_id`** everywhere for a given conversation (e.g. `C12345678` for DM, `G12345` for group). Chat IDs come from `loadChats` and from `startChat` when creating a new DM.

---

## 3. WebSocket: connect, send, and receive

- **URL:** `ws://<host>/ws/chat/` (dev), `wss://<host>/ws/chat/` (prod), same host as REST.
- **When to connect:** After the user is logged in (e.g. when the main app or messaging layout mounts). If the connection closes with code **4001**, treat as unauthenticated and redirect to login or show an error.
- **When to send (outgoing):** See Section 4. All messages are JSON; send with `wsRef.current.send(JSON.stringify({ type, chat_id, ... }))`.
- **When to receive (incoming):** In the WebSocket `onmessage` handler, parse `event.data` as JSON and branch on `data.type` to update React state (see Section 5). Do **not** send message content over the WebSocket; sending is done only via REST **POST postMessages**.

Outgoing message types (from api_testing.md):

- `subscribe` — `{ "type": "subscribe", "chat_id": "<chat_id>" }`
- `unsubscribe` — `{ "type": "unsubscribe", "chat_id": "<chat_id>" }`
- `mark_seen` — `{ "type": "mark_seen", "chat_id": "<chat_id>" }` or with `"user_id": "<logged_in_username>"`
- `typing_start` — `{ "type": "typing_start", "chat_id": "<chat_id>" }`
- `typing_stop` — `{ "type": "typing_stop", "chat_id": "<chat_id>" }`

Incoming event types you must handle: `unseen_count_updated`, `new_message`, `chat_updated`, `messages_seen`, `user_typing`, `error`. Exact payloads and recommended client actions are in **api_testing.md**, Section 7 (“Client implementation guide”).

---

## 4. Execution order (when to call APIs and send WebSocket messages)

Follow this order so the chat list, messages, and unseen counts stay in sync with the backend. This matches **Section 7** of api_testing.md.

1. **App load / after login**
   - Open WebSocket to `/ws/chat/`.
   - On `open`, optionally call **GET /messaging/loadChats/** and store the result in state (or context) for the inbox. Use `Group_info` and `chats_info`; use `unseen_count` for badges.

2. **User opens a chat (DM or group)**
   - Send **subscribe:** `{ "type": "subscribe", "chat_id": "<chat_id>" }`.
   - Then call **GET /messaging/getMessages/<chat_id>/**; on 200, set the message list state for this chat and render it.
   - As soon as getMessages succeeds, send **mark_seen:** `{ "type": "mark_seen", "chat_id": "<chat_id>" }` (and optionally `"user_id": "<logged_in_username>"`). The server will persist “seen” and reply with **unseen_count_updated** (0) so you can update the badge without calling loadChats again.

3. **User sends a message**
   - Call **POST /messaging/postMessages/<chat_id>/** with body `{ "Message": "..." }` and/or `{ "attachment_ids": [...] }`. Do **not** send anything over the WebSocket for sending. On 201, the server will broadcast **new_message** and **chat_updated**; your WebSocket handler will receive them and can append the message and update the list row (or use optimistic UI and then reconcile with **new_message**).

4. **User leaves the chat screen**
   - Send **unsubscribe:** `{ "type": "unsubscribe", "chat_id": "<chat_id>" }` so you stop receiving events for that chat.

5. **Typing indicators (optional)**
   - When the user starts typing in the input: send **typing_start** once (e.g. debounced 300–500 ms): `{ "type": "typing_start", "chat_id": "<chat_id>" }`.
   - When the user stops (blur or idle ~2–3 s): send **typing_stop:** `{ "type": "typing_stop", "chat_id": "<chat_id>" }`. If you don’t, the server will clear typing after ~8 s.

---

## 5. Handling WebSocket events in React

In your WebSocket `onmessage` handler, parse `event.data` as JSON and update state (or context) as follows. This mirrors the “WebSocket message handler” table in api_testing.md.

- **unseen_count_updated** — Update the unseen count for `data.chat_id` in your chat list state (e.g. a map `chatId -> unseenCount`). If `data.unseen_count === 0`, clear the badge for that chat. Use this both after your own **mark_seen** and when others post (recipients get this event).
- **new_message** — Append `data.message` to the message list for `data.chat_id`. If this chat is currently open, re-render the list and optionally scroll to bottom; if the sender is not the current user, optionally play a sound.
- **chat_updated** — Update the chat list row for `data.chat_id`: set `last_message_at`, `last_message_preview`, and optionally `unseen_count` from the event so the list reflects the latest activity without refetching loadChats.
- **messages_seen** — Optional: show “Seen by …” or read receipts using `data.seen_by`, `data.seen_by_name`, `data.message_ids` / `data.last_seen_message_id`, `data.seen_at`.
- **user_typing** — If `data.is_typing === true`, show “`data.user_name` is typing…” for `data.chat_id`; if `false`, hide it. Typing state can be stored per chat (e.g. `typingUser` or `typingByChatId[chatId]`).
- **error** — Show `data.message` to the user (toast or inline).

Keep the WebSocket instance in a ref (or context) so the same connection is used for subscribe/unsubscribe/mark_seen/typing and for receiving these events. When the user logs out or the app unmounts, close the WebSocket and clean up.

---

## 6. Suggested React structure (concise)

- **State (or context):**
  - `chatList`: from loadChats (`Group_info`, `chats_info`) with `unseen_count` per chat.
  - `messagesByChatId`: map of `chatId -> message[]` (from getMessages and from **new_message**).
  - `activeChatId`: currently open chat (for subscribe/mark_seen/unsubscribe and for showing typing).
  - `typingByChatId`: map of `chatId -> { user_name, is_typing }` (or similar) for **user_typing**.
  - `unseenCountByChatId`: map of `chatId -> number` (from loadChats and **unseen_count_updated**).
- **WebSocket:** Create once after login (e.g. in a provider or top-level effect), store in a ref, and pass a “send” function and/or the ref to components that need to subscribe/mark_seen/typing. In `onmessage`, dispatch updates to the above state (or context setters).
- **Lifecycle:** On “open chat”, run: send subscribe → fetch getMessages → set messages → send mark_seen. On “leave chat” (navigate away or close panel), send unsubscribe. On unmount or logout, close the WebSocket.

---

## 7. Checklist for implementation

- [ ] Base URL and WebSocket URL from env; same host for REST and WS.
- [ ] All REST calls use `credentials: 'include'` (or equivalent) so the session cookie is sent.
- [ ] Connect WebSocket after login; on close code 4001, treat as unauthenticated.
- [ ] loadChats after WS open; store Group_info and chats_info; show unseen_count as badges.
- [ ] On open chat: send subscribe → GET getMessages → set messages → send mark_seen; handle unseen_count_updated to set badge to 0.
- [ ] On send message: POST postMessages only; handle new_message and chat_updated from WS to update UI.
- [ ] On leave chat: send unsubscribe.
- [ ] Optional: typing_start / typing_stop with debounce; handle user_typing to show “X is typing”.
- [ ] Optional: handle messages_seen for read receipts; handle error and show message to user.

For exact request/response shapes, status codes, and example payloads, always refer to **`Messaging/api_testing.md`**.
