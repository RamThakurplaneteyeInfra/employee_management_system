# Messaging APIs – Testing reference (Postman)

**Base URL:** `{{baseurl}}/messaging/`  
**Auth:** All endpoints require a **logged-in user** (session/cookie).  
**Note:** Call APIs (1:1 and group calls) live under the same `/messaging/` prefix; see **Calling/api_testing.md** for call endpoints.

---

## 1. Group management

### Create group

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

---

### Show created groups

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/showCreatedGroups/` |

No body. Returns groups created by the logged-in user.

**Success (200):** Array of `{ "group_id": "...", "total_participant": N, "name": "...", "description": "...", "created_at": "dd/mm/yyyy, HH:MM:SS" }` (IST).

---

### Show group members

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/showGroupMembers/<group_id>/` |

Replace `<group_id>` with the group’s `group_id` (e.g. `G-xxx`).

**Success (200):** Array of objects with `participant` (username), `participant_name` (Profile name), `groupchat`.

---

### Add user to group

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/addUser/<group_id>/` |

**Body (JSON):**
```json
{
  "participant": "username_to_add"
}
```

**Success (200):** Group member list or success response. **302** if user already in group.

---

### Delete user from group

| Method | URL |
|--------|-----|
| DELETE | `{{baseurl}}/messaging/deleteUser/<group_id>/<user_id>/` |

`<user_id>` is the username to remove.

**Success (202):** User removed. **403** if not allowed.

---

### Delete group

| Method | URL |
|--------|-----|
| DELETE | `{{baseurl}}/messaging/deleteGroup/<group_id>/` |

**Success (202):** `{ "message": "group deleted successfully" }`  
**403** if user is not allowed to delete the group.

---

## 2. Chats and messages

### Start or get individual chat

| Method | URL |
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

---

### Post message (group or individual)

| Method | URL |
|--------|-----|
| POST   | `{{baseurl}}/messaging/postMessages/<chat_id>/` |

`<chat_id>` is either a group id (e.g. `G-xxx`) or an individual `chat_id`.  
Send at least one of: **Message** (text) or **attachment_ids** (ids from uploadFile/addLink).

**Body (JSON) – message only:**
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

---

### Get messages

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/getMessages/<chat_id>/` |

**Success (200):** Response shape depends on implementation; typically list of messages with `message`, `attachments`, `quote` (if any), sender info, timestamps in IST.

---

### Load groups and chats (inbox)

| Method | URL |
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

---

### Delete attachment

| Method | URL |
|--------|-----|
| DELETE | `{{baseurl}}/messaging/attachments/<attachment_id>/` |

Only the uploader can delete; only **unlinked** attachments (not yet sent in a message) can be deleted.

**Success (200):** `{ "message": "Attachment deleted" }`  
**Errors:** 403 not allowed; 404 not found; 400 if attachment already sent.

---

### Get attachment URL

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/messaging/files/<attachment_id>/url/` |

Returns a URL to view/download the file or link. User must have access (member of group/chat or owner of unlinked attachment).

**Success (200):** `{ "url": "...", "file_name": "...", "type": "file" }` or `"type": "link"` for links.

---

## 4. Calling APIs (under same prefix)

All call-related endpoints (callableUsers, initiateCall, acceptCall, declineCall, endCall, screenShare, stopScreenShare, missedCallsCount, resetMissedCallsCount, pendingCalls, activeCalls, endAllMyCalls, initiateGroupCall, joinGroupCall, leaveGroupCall, endGroupCall, activeGroupCalls, callHistory) are documented in **Calling/api_testing.md**.  
Base path for those: `{{baseurl}}/messaging/` (e.g. `{{baseurl}}/messaging/initiateCall/`).

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
| Load chats        | GET    | `/messaging/loadChats/` |
| Upload file       | POST   | `/messaging/uploadFile/` |
| Add link          | POST   | `/messaging/addLink/` |
| Delete attachment | DELETE | `/messaging/attachments/<attachment_id>/` |
| Get attachment URL| GET    | `/messaging/files/<attachment_id>/url/` |
