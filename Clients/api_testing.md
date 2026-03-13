# Clients APIs – Testing reference

Base prefix: `{{baseurl}}/clients/` (or whichever prefix you mount `Clients/urls.py` under).

Use this file to document all executable APIs in the `Clients` app (client profiles, stages, conversations).

---

## 1. Client stages

Endpoints to list or manage `Current_client_stage` entries.

> Add URLs, methods, and sample responses for stage listing and any admin operations.

---

## 2. Client profiles

Endpoints for `ClientProfile`:

- Create / update / delete client profiles.
- List and filter by `status`, `Product`, `created_by`, etc.

> Document base URLs, request bodies, and typical responses.

---

## 3. Client conversations (notes + interaction channels)

Endpoints for `ClientConversation` and `ClientInteractionChannels`:

- Add conversation notes for a client, optionally tagged with an interaction **medium**.
- List conversations for a given client, including the selected **medium**.

### 3.1 Interaction channels (seeded master data)

The following interaction channels are pre-seeded in `ClientInteractionChannels.medium`:

- `Calls`
- `Trial`
- `Demand`
- `Pitch`

You don’t need an explicit API to create them; they are inserted by migration. The client should **treat these as a fixed set of allowed values** for now.

### 3.2 List conversations for a client

- **URL:** `{{baseurl}}/clients/profiles/<profile_id>/conversations/`
- **Method:** `GET`

**Example response:**

```json
[
  {
    "id": 101,
    "note": "Had an introductory call with the client.",
    "created_by": "john_doe",
    "created_at": "09/03/2026 15:30:00",
    "medium": "Calls"
  },
  {
    "id": 102,
    "note": "Shared trial account details.",
    "created_by": "john_doe",
    "created_at": "09/03/2026 16:00:00",
    "medium": "Trial"
  }
]
```

Notes:

- `medium` is always returned as the **full name** of the interaction channel (e.g. `"Calls"`, `"Trial"`, `"Demand"`, `"Pitch"`), or `null` if no medium was set.

### 3.3 Add conversations for a client

- **URL:** `{{baseurl}}/clients/profiles/<profile_id>/conversations/`
- **Method:** `POST`

You can either send a **single note** or an array of **multiple notes**. In both cases, you can pass an optional `medium` field with the **full channel name**.

#### 3.3.1 Single note

**Request body:**

```json
{
  "note": "Explained pricing and discount structure.",
  "medium": "Pitch"
}
```

- `note` (string, required): Conversation text.
- `medium` (string, optional): One of `"Calls"`, `"Trial"`, `"Demand"`, `"Pitch"`. Case-insensitive match.

**Example success response:**

```json
{
  "id": 123,
  "message": "Note added"
}
```

If `medium` is provided but does not match any existing channel, the API returns:

```json
{
  "error": "Invalid medium"
}
```

#### 3.3.2 Multiple notes in one request

**Request body:**

```json
{
  "notes": [
    "Initial discovery call done.",
    "Shared trial link with the client."
  ],
  "medium": "Trial"
}
```

- `notes` (array of strings, required): At least one non-empty note.
- `medium` (string, optional): Same rules as above (full name, case-insensitive).

**Example success response:**

```json
{
  "ids": [201, 202],
  "message": "2 note(s) added"
}
```

If `notes` is empty, the API returns:

```json
{
  "error": "notes array cannot be empty"
}
```

If `medium` is invalid, you get the same `"Invalid medium"` error as for the single-note POST.

### 3.4 Update / delete a conversation

- **URL:** `{{baseurl}}/clients/profiles/<profile_id>/conversations/<note_id>/`
- **Methods:**
  - `PATCH` – update `note`
  - `DELETE` – delete conversation

Currently only the `note` text is updatable via `PATCH`; `medium` is not exposed for update.

