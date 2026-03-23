# Messaging & Calling APIs – Testing reference

**Base prefix:** `{{baseurl}}/messaging/`  
**Auth:** All endpoints require a logged-in user (session/cookie).  
**Content-Type:** `application/json` for JSON bodies; `multipart/form-data` for file upload.

Call and messaging APIs share the same base path (e.g. `{{baseurl}}/messaging/initiateCall/`).  
For React integration and WebSocket chat flow, see **`Messaging/REACT_INTEGRATION_PROMPT.md`**.

---

## 1. Group management

### createGroup

**url:** `{{baseurl}}/messaging/createGroup/`  
**method:** POST  
**body:**
```json
{
  "group_name": "My Team",
  "description": "Optional description",
  "participants": ["user1", "user2"]
}
```
**sample_response:**
```json
{ "Messsage": "Group created successfully" }
```
**notes:** `group_name` and `participants` (at least one username) required. Participants can be array or object with indices. 201 on success; 403/406 on permission or invalid participants.

---

### showCreatedGroups

**url:** `{{baseurl}}/messaging/showCreatedGroups/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "group_id": "G-xxx",
    "total_participant": 3,
    "name": "My Team",
    "description": "Optional",
    "created_at": "09/03/2026 14:30:00"
  }
]
```
**notes:** Groups created by the logged-in user. Times in IST.

---

### showGroupMembers

**url:** `{{baseurl}}/messaging/showGroupMembers/<group_id>/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "participant": "user1", "participant_name": "Full Name 1", "groupchat": true }
]
```
**notes:** Replace `<group_id>` with group id (e.g. G-xxx). 403 if not a member.

---

### addUser

**url:** `{{baseurl}}/messaging/addUser/<group_id>/`  
**method:** POST  
**body:**
```json
{ "participant": "username_to_add" }
```
**sample_response:** Group member list or success.  
**notes:** 302 if user already in group; 403 if not allowed.

---

### deleteUser

**url:** `{{baseurl}}/messaging/deleteUser/<group_id>/<user_id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 202 with success message.  
**notes:** `<user_id>` is the username to remove. 403 if not allowed.

---

### deleteGroup

**url:** `{{baseurl}}/messaging/deleteGroup/<group_id>/`  
**method:** DELETE  
**body:** None  
**sample_response:**
```json
{ "message": "group deleted successfully" }
```
**notes:** 202 on success. 403 if user cannot delete the group.

---

## 2. Chats and messages

### startChat

**url:** `{{baseurl}}/messaging/startChat/`  
**method:** POST  
**body:**
```json
{ "participant": "other_username" }
```
**sample_response:** If existing chat: `{ "chat_id": "...", "participant": "<Full Name>", "messages": {} }`. If new: message list for the new chat (same structure as getMessages).  
**notes:** Creates or returns existing DM with the given user.

---

### postMessages

**url:** `{{baseurl}}/messaging/postMessages/<chat_id>/`  
**method:** POST  
**body (text):**
```json
{ "Message": "Hello everyone." }
```
**body (with attachments):**
```json
{ "Message": "See the file.", "attachment_ids": [1, 2] }
```
**body (attachments only):**
```json
{ "attachment_ids": [1] }
```
**body (reply to a message):**
```json
{
  "Message": "Agreed, thanks!",
  "replyTo": 930,
  "attachment_ids": []
}
```
**sample_response:**
```json
{ "message": "Message sent successfully" }
```
**notes:** `<chat_id>` is group id (e.g. G-xxx) or individual chat_id. Send at least one of `Message` (or lowercase `message`) or `attachment_ids`. `replyTo` (or `reply_to`) is optional but must point to an existing message in the same chat/group; when `replyTo` is provided, the new post must include non-empty text. Attachment ids from uploadFile/addLink. 201 on success; 400 if invalid chat or neither Message/message nor attachment_ids.

---

### getMessages

**url:** `{{baseurl}}/messaging/getMessages/<chat_id>/`  
**method:** GET  
**body:** None  
**sample_response:** Array of messages with `message`, `attachments`, `quote`, sender info, timestamps in IST; DM messages may include `seen`.  
**notes:** Only participants. Includes reply-to fields when present: `replyTo` (parent id or null) and `repliedMessage` (`{id, message, sender}` or null).

---

### markSeen

**url:** `{{baseurl}}/messaging/markSeen/<chat_id>/`  
**method:** POST  
**body:** `{}` or `{ "message_ids": [101, 102] }` or `{ "last_message_id": 103 }`. Empty body = mark all in chat as seen.  
**sample_response:**
```json
{ "status": "ok" }
```
**notes:** Participant only. Persisted; WebSocket clients receive messages_seen. 403 if not a participant.

---

### loadChats

**url:** `{{baseurl}}/messaging/loadChats/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{
  "Group_info": [
    {
      "group_id": "...",
      "group_name": "...",
      "description": "...",
      "total_participant": 2,
      "last_message_at": "09/03/26 14:30:00",
      "unseen_count": 0
    }
  ],
  "chats_info": [
    {
      "chat_id": "...",
      "with": "Other User Full Name",
      "last_message_at": "09/03/26 14:30:00",
      "unseen_count": 0
    }
  ]
}
```
**notes:** Groups and DMs for logged-in user, ordered by last activity. Times in IST.

---

## 3. Attachments

### uploadFile

**url:** `{{baseurl}}/messaging/uploadFile/`  
**method:** POST  
**body:** `multipart/form-data`; field name `file`.  
**sample_response:**
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
**notes:** Use `id` in `attachment_ids` when posting a message. 201 on success.

---

### addLink

**url:** `{{baseurl}}/messaging/addLink/`  
**method:** POST  
**body:**
```json
{
  "url": "https://example.com/page",
  "title": "Optional link title"
}
```
**sample_response:**
```json
{ "id": 2, "url": "https://example.com/page", "title": "Optional link title" }
```
**notes:** `title` can be sent as `link_title`. Use `id` in `attachment_ids` when posting. 201 on success.

---

### delete attachment

**url:** `{{baseurl}}/messaging/attachments/<attachment_id>/`  
**method:** DELETE  
**body:** None  
**sample_response:**
```json
{ "message": "Attachment deleted" }
```
**notes:** Only uploader; only unlinked attachments (not yet sent in a message). 403/404/400 if not allowed or already sent.

---

### get attachment URL

**url:** `{{baseurl}}/messaging/files/<attachment_id>/url/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{ "url": "...", "file_name": "...", "type": "file" }
```
**notes:** For links, `type` is `"link"`. Caller must have access (member of group/chat or owner of unlinked attachment).

---

## 4. Calling – 1:1 calls

### callableUsers

**url:** `{{baseurl}}/messaging/callableUsers/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "username": "user1", "name": "Full Name 1", "is_busy": false },
  { "username": "user2", "name": "Full Name 2", "is_busy": true }
]
```
**notes:** All users with Profile except self; `is_busy` true if in pending/accepted call.

---

### initiateCall

**url:** `{{baseurl}}/messaging/initiateCall/`  
**method:** POST  
**body:**
```json
{ "user_id": "receiver_username", "call_type": "audio" }
```
**sample_response:**
```json
{
  "success": true,
  "call_id": 1,
  "call_type": "audio",
  "sender": "caller_username",
  "receiver": "receiver_username"
}
```
**notes:** `call_type`: `audio` or `video`. Cannot call self. 201 on success; 400/404/409 (receiver busy).

---

### acceptCall

**url:** `{{baseurl}}/messaging/acceptCall/`  
**method:** POST  
**body:**
```json
{ "call_id": 1 }
```
**sample_response:**
```json
{
  "success": true,
  "call_id": 1,
  "sender": "caller_username",
  "receiver": "receiver_username"
}
```
**notes:** Receiver only. 403 if not receiver; 400 if call not pending.

---

### declineCall

**url:** `{{baseurl}}/messaging/declineCall/`  
**method:** POST  
**body:**
```json
{ "call_id": 1 }
```
**sample_response:**
```json
{
  "success": true,
  "call_id": 1,
  "sender": "caller_username",
  "receiver": "receiver_username"
}
```
**notes:** Receiver only. 403 if not receiver; 400 if call not pending.

---

### endCall

**url:** `{{baseurl}}/messaging/endCall/`  
**method:** POST  
**body:**
```json
{ "call_id": 1 }
```
**sample_response:**
```json
{
  "success": true,
  "call_id": 1,
  "sender": "caller_username",
  "receiver": "receiver_username"
}
```
**notes:** Caller or receiver. Pending call becomes MISSED; accepted becomes ENDED. Other party notified via WebSocket.

---

### screenShare

**url:** `{{baseurl}}/messaging/screenShare/`  
**method:** PATCH  
**body:**
```json
{ "call_id": 1 }
```
**sample_response (1:1):**
```json
{
  "is_screen_shared": true,
  "shared_by_name": "Full Name",
  "call_id": 1,
  "other_username": "other_username",
  "kind": "call"
}
```
**notes:** Participant only. Use `call_id` for 1:1 or `group_call_id` for group call; not both. 400 if call not active.

---

### stopScreenShare

**url:** `{{baseurl}}/messaging/stopScreenShare/`  
**method:** PATCH  
**body:**
```json
{ "call_id": 1 }
```
**sample_response:**
```json
{
  "is_screen_shared": false,
  "stopped_by_name": "Full Name",
  "call_id": 1,
  "other_username": "other_username",
  "kind": "call"
}
```
**notes:** Same as screenShare; use `call_id` or `group_call_id`.

---

### pendingCalls

**url:** `{{baseurl}}/messaging/pendingCalls/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "call_id": 1,
    "sender": "caller_username",
    "receiver": "receiver_username",
    "call_type": "audio",
    "status": "PENDING",
    "is_screen_shared": false,
    "timestamp": "09/03/2026 14:30:00"
  }
]
```
**notes:** Incoming calls for current user (receiver, status PENDING). Times in IST.

---

### activeCalls

**url:** `{{baseurl}}/messaging/activeCalls/`  
**method:** GET  
**body:** None  
**sample_response:** Same shape as pendingCalls; includes PENDING and ACCEPTED where user is sender or receiver.  
**notes:** Use `call_id` with endCall to clear stuck calls.

---

### missedCallsCount

**url:** `{{baseurl}}/messaging/missedCallsCount/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{ "missed_calls_count": 3 }
```
**notes:** From MissedCallCount for current user.

---

### resetMissedCallsCount

**url:** `{{baseurl}}/messaging/resetMissedCallsCount/`  
**method:** POST  
**body:** None (or empty JSON)  
**sample_response:**
```json
{ "success": true, "missed_calls_count": 0 }
```
**notes:** Sets missed count to 0 and invalidates cache.

---

### endAllMyCalls

**url:** `{{baseurl}}/messaging/endAllMyCalls/`  
**method:** POST  
**body:** None (or empty JSON)  
**sample_response:**
```json
{ "success": true, "ended_count": 2, "message": "Ended 2 call(s)." }
```
**notes:** Ends all active (pending/accepted) 1:1 calls for current user.

---

## 5. Calling – Group calls

### initiateGroupCall

**url:** `{{baseurl}}/messaging/initiateGroupCall/`  
**method:** POST  
**body:**
```json
{ "user_ids": ["user1", "user2"], "call_type": "audio" }
```
**sample_response:**
```json
{
  "success": true,
  "call_id": 1,
  "creator": "creator_username",
  "call_type": "audio",
  "participant_usernames": ["user1", "user2"]
}
```
**notes:** `call_type`: `audio` or `video`. At least one other user required; creator auto-joined. Invitees get WebSocket incoming_group_call. 201 on success.

---

### joinGroupCall

**url:** `{{baseurl}}/messaging/joinGroupCall/`  
**method:** POST  
**body:**
```json
{ "call_id": 1 }
```
**sample_response:**
```json
{
  "success": true,
  "call_id": 1,
  "creator": "creator_username",
  "call_type": "audio",
  "participant_usernames": ["creator", "user1"]
}
```
**notes:** Must be invited. 403 if not participant; 400 if call ended.

---

### leaveGroupCall

**url:** `{{baseurl}}/messaging/leaveGroupCall/`  
**method:** POST  
**body:**
```json
{ "call_id": 1 }
```
**sample_response:** Success payload with updated participant list or similar.  
**notes:** Participant leaves; others notified via WebSocket.

---

### endGroupCall

**url:** `{{baseurl}}/messaging/endGroupCall/`  
**method:** POST  
**body:**
```json
{ "call_id": 1 }
```
**sample_response:** Success message.  
**notes:** Creator only. Ends call for all; participants notified.

---

### activeGroupCalls

**url:** `{{baseurl}}/messaging/activeGroupCalls/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "call_id": 1,
    "creator": "creator_username",
    "call_type": "audio",
    "status": "ACTIVE",
    "is_screen_shared": false,
    "created_at": "09/03/2026 14:30:00",
    "participants_joined": ["creator", "user1"],
    "participants_invited": ["user2"]
  }
]
```
**notes:** Active group calls where current user is creator or participant (invited or joined). Times in IST.

---

### callHistory

**url:** `{{baseurl}}/messaging/callHistory/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "call_kind": "individual",
    "id": 1,
    "sender": "user1",
    "receiver": "user2",
    "call_type": "audio",
    "status": "ENDED",
    "is_screen_shared": false,
    "timestamp": "09/03/2026 14:30:00",
    "initiator": true,
    "initiator_name": "User One",
    "participant": ["User One", "User Two"]
  },
  {
    "call_kind": "group",
    "id": 2,
    "creator": "user1",
    "call_type": "video",
    "status": "ENDED",
    "is_screen_shared": false,
    "created_at": "09/03/2026 15:00:00",
    "initiator": false,
    "initiator_name": "User One",
    "participant": ["User One", "User Two", "User Three"]
  }
]
```
**notes:** Individual and group calls for current user, newest first. Timestamps in IST.

---

## 6. Chat WebSocket (reference)

**url:** `ws://<host>/ws/chat/` (or `wss://` in prod). Session cookie required; 4001 if not logged in.

**Client → Server:** `subscribe` / `unsubscribe` (chat_id), `typing_start` / `typing_stop`, `mark_seen` (chat_id; optional user_id).  
**Server → Client:** `new_message`, `chat_updated`, `messages_seen`, `user_typing`, `unseen_count_updated`, `error`.

Recommended order: connect WS → loadChats; on open chat: subscribe → getMessages → mark_seen; on send: POST postMessages only; on leave: unsubscribe.  
See **`Messaging/REACT_INTEGRATION_PROMPT.md`** for full flows and handlers.
