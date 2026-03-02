# Messaging APIs – Postman reference

Base URL: `http://localhost:8000` (or your server).  
All endpoints under `/messaging/` require **logged-in user** (session/cookie auth).

---
## 1. Upload file
<!--
Upload a file to S3 and create an unlinked attachment. Use the returned `id` in **Post message** to attach it to a message.

| Field   | Value |
|--------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/messaging/uploadFile/` |

**Headers**
- None required beyond session cookie (login first).

**Body** – `form-data`
| Key  | Type | Required | Description |
|------|------|----------|-------------|
| file | File | Yes      | The file to upload (any type). |

**Success response** – `201 Created`
```json
{
  "id": 42,
  "s3_key": "files/messaging/abc123def456.png",
  "file_name": "screenshot.png",
  "content_type": "image/png",
  "file_size": 12345,
  "url": "https://...presigned-url..."
}
``` -->
<!-- 
**Error examples**
- `400` – `{"error": "No file provided"}`
- `500` – `{"error": "Upload failed: ..."}`

--- -->

 ## 2. Add link
<!--
Create an unlinked link attachment. Use the returned `id` in **Post message** to attach it.

| Field   | Value |
|--------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/messaging/addLink/` |

**Headers**
- `Content-Type: application/json`

**Body** – raw JSON
```json
{
  "url": "https://example.com/article",
  "title": "Optional display title"
}
```
| Key   | Type   | Required | Description |
|-------|--------|----------|-------------|
| url   | string | Yes      | The shared URL. |
| title | string | No       | Display title (can also use `link_title`). |

**Success response** – `201 Created`
```json
{
  "id": 43,
  "url": "https://example.com/article",
  "title": "Optional display title"
}
```

**Error examples**
- `400` – `{"error": "url is required"}`

--- -->

## 3. Delete attachment
<!--
Delete an uploaded file or link that has **not** been sent yet. Only the uploader can delete. For files, the object is removed from S3.

| Field   | Value |
|--------|--------|
| **Method** | `DELETE` |
| **URL**    | `{{baseurl}}/messaging/attachments/<attachment_id>/` |

**Example:** `DELETE http://localhost:8000/messaging/attachments/42/`

**Headers**
- None required beyond session cookie.

**Body**
- None.

**Success response** – `200 OK`
```json
{
  "message": "Attachment deleted"
}
```

**Error examples**
- `400` – `{"error": "Cannot delete attachment that is already sent"}`
- `403` – `{"error": "Not allowed"}`
- `404` – Attachment not found.

--- -->

## 4. Get attachment URL
<!-- 
Get a URL for an attachment (presigned for files, direct for links). User must have access to the conversation (group member or chat participant).

| Field   | Value |
|--------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/messaging/files/<attachment_id>/url/` |

**Example:** `GET http://localhost:8000/messaging/files/42/url/`

**Headers**
- None required beyond session cookie.

**Body**
- None.

**Success response** – `200 OK`

For a **file** attachment:
```json
{
  "url": "https://...presigned-s3-url...",
  "file_name": "screenshot.png",
  "type": "file"
}
```

For a **link** attachment:
```json
{
  "url": "https://example.com/article",
  "file_name": "Optional display title",
  "type": "link"
}
```

**Error examples**
- `403` – `{"error": "Not allowed"}`
- `404` – Attachment not found.

--- -->

## 5. Post message

Send a **text message** and/or **existing attachment IDs** (JSON only). Simple flow: upload file first (Upload file / Add link), get `id`, then post message with optional `attachment_ids`.

| Field   | Value |
|--------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/messaging/postMessages/<chat_id>/` |

**chat_id**
- Group: e.g. `G12345`
- Individual: e.g. `C12345678`

**Headers:** `Content-Type: application/json`

**Body** – raw JSON
```json
{
  "Message": "Hello, here is the document",
  "attachment_ids": [42]
}
```

| Key            | Type   | Required | Description |
|----------------|--------|----------|-------------|
| Message        | string | No*      | Message text. |
| attachment_ids | array  | No*      | IDs from **Upload file** or **Add link** (first ID is linked to the message if Message is also sent). |

\* At least one of `Message` or `attachment_ids` must be present. **Message only:** stored in GroupMessages/Chats with `attachment` NULL. **Files only:** attachments are stored in MessageAttachments with group/chat set (no message row). **Message + files:** one message is created with the first attachment ID as reference; other IDs can be used in a follow-up or are stored as attachment-only.

**Success response** – `201 Created`
```json
{
  "message": "Message sent successfully"
}
```

**Error examples**
- `204` – `{"message": "Message or attachments required"}`
- `400` – `{"message": "Invalid chat/group id"}`

---

## 6. Get messages

Fetch the unified timeline for a group or individual chat. Each item is either a message (with optional attachments) or an attachment-only entry (file/link sent without text). Each message includes attachments; file attachments include a presigned `url` so you don’t need to call **Get attachment URL** for each file.

| Field   | Value |
|--------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/messaging/getMessages/<chat_id>/` |

**Example:** `GET http://localhost:8000/messaging/getMessages/G12345/`

**Headers**
- None required beyond session cookie.

**Body**
- None.

**Success response** – `200 OK`

Response is an **array** of timeline items, newest first. Each item has: `id` (number or `null`), `sender`, `message`, `date`, `time`, `attachments` (array).

- **Message (text only):** `id` set, `message` filled, `attachments` empty.
- **Message with file:** `id` set, `message` filled, `attachments` has one item (attachment payload).
- **Attachment-only:** `id` null, `message` empty, `attachments` has one or more file/link objects.

**Example:**
```json
[
  {
    "id": 101,
    "sender": "John Doe",
    "message": "Hello, here is the document",
    "date": "17/02/26",
    "time": "14:30:45",
    "attachments": [
      { "id": 42, "type": "file", "file_name": "screenshot.png", "url": "https://...presigned..." }
    ]
  },
  {
    "id": null,
    "sender": "Jane Doe",
    "message": "",
    "date": "17/02/26",
    "time": "14:35:00",
    "attachments": [
      { "id": 44, "type": "file", "file_name": "report.pdf", "url": "https://...presigned..." }
    ]
  }
]
```

**Example – attachment-only item:** same shape as above, with `id` null and `message` empty.

**Attachment types**
- `type: "file"` – `id`, `file_name`, `url` (presigned).
- `type: "link"` – `id`, `url`, `title`.

**Error examples**
- `403` – `{"message": "you are not authorised to accessed this conversation"}`

---

## 7. Load chats (groups and DMs)

Load all groups and individual chats for the logged-in user, ordered by `last_message_at` (most recent first), with unseen message count per conversation.

| Field   | Value |
|--------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/messaging/loadChats/` |

**Headers**
- None required beyond session cookie.

**Body**
- None.

**Success response** – `200 OK`  
Returns a JSON object with keys such as `group_info` (list of groups) and `chat_info` (list of individual chats). Each item includes conversation metadata and `unseen_count` (or equivalent). Exact shape depends on your `_load_groups_and_chats_sync` implementation.

---

## Quick flow for Postman

1. **Login** (your existing auth endpoint) so the session cookie is set.
2. **Upload file:** `POST /messaging/uploadFile/` → form-data, key `file` → note `id`.
3. **Optional – Add link:** `POST /messaging/addLink/` → JSON `{"url": "https://...", "title": "..."}` → note `id`.
4. **Optional – Delete before sending:** `DELETE /messaging/attachments/<id>/` if user removes an attachment.
5. **Send message:** `POST /messaging/postMessages/<chat_id>/` → Body raw JSON `{"Message": "Hi", "attachment_ids": [42]}`. At least one of `Message` or `attachment_ids` required. Upload file first, then send message with returned `id`.
6. **Get messages:** `GET /messaging/getMessages/<chat_id>/` → list of timeline items (messages and/or attachment-only); each may have `attachments` with file `url`s.
7. **Load chats:** `GET /messaging/loadChats/` → groups and DMs ordered by last activity, with unseen counts.
8. **Get single attachment URL (optional):** `GET /messaging/files/<attachment_id>/url/` when you need a fresh presigned URL.
