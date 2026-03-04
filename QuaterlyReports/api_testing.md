# Quaterly Reports – Actionable Entries APIs (Testing reference)

Base URL: `http://localhost:8000` (or your server).  
Endpoints below are at the **root** (e.g. `/ActionableEntries/`).  
All require **logged-in user** (session/cookie auth).

---

## Status and share chain

- **Final status (creator):** `final_Status` on the entry. Default **PENDING** at creation. After **co-author approves** → **INPROCESS**. Creator can set to **COMPLETED** when done (final status from creator).
- **Share chain:** Stored in `FunctionsEntriesShare`. First `share_with` is set by the creator at create. Others are added via **Share further**. Each row has: `shared_with`, `note`, `shared_time`, `individual_status`.
- **Who shares further:** Anyone already in the share chain. When they share, their **individual_status** is set to **INPROCESS**. The **last** person in the chain can set their **individual_status** to **COMPLETED**; then no further sharing is allowed.
- **No further sharing** when: any share row has status **COMPLETED**, or entry **final_Status** is **COMPLETED**.

---

## 1. List / Create actionable entries

| Field    | Value |
|----------|--------|
| **Method** | `GET` (list) \| `POST` (create) |
| **URL**    | `{{baseurl}}/ActionableEntries/` |

### GET – List

**Query (optional):** `username`, `month`. If not superuser, only own entries (and month) are allowed.

**Success (200):** Array of entry objects, each with `share_chain` (array of `{ id, shared_with, shared_with_username, note, shared_time, individual_status, individual_status_name }`).

### POST – Create

**Headers:** `Content-Type: application/json`

**Body (example):**

```json
{
  "goal": 1,
  "co_author": "jane",
  "share_with": "bob",
  "date": "2026-03-15",
  "note": "Entry note.",
  "final_Status": null
}
```

| Key          | Type   | Required | Description |
|--------------|--------|----------|-------------|
| goal         | int    | No       | ActionableGoals PK. |
| co_author    | string | No       | Username of co-author. |
| share_with   | string | No       | Username of **first** share recipient (creates first row in share chain). |
| date         | string | Yes      | YYYY-MM-DD. |
| note         | string | Yes      | Entry note. |
| final_Status | string | No       | Default PENDING. |

**Success (201):** Created entry with `share_chain` (one item if `share_with` was provided).

---

## 2. Get / Update / Delete one entry

| Field    | Value |
|----------|--------|
| **Method** | `GET` \| `PUT` \| `PATCH` \| `DELETE` |
| **URL**    | `{{baseurl}}/ActionableEntriesByID/<id>/` |

**Visibility:** Creator, co_author, or any user in `share_chain` (and `approved_by_coauthor=True`).

### PATCH – Update (creator / co_author)

Creator or co_author can update entry fields (e.g. `note`, `final_Status`, `co_author`). Creator can set `final_Status` to **COMPLETED** when done.

### PATCH – Update (share-chain user)

If the current user is in the share chain (and not creator/co_author), only these body fields are applied:

- **share_note** – update this user’s share row `note`.
- **individual_status** – set this user’s share row status (e.g. `"COMPLETED"`). **Only the last person in the chain** can set **COMPLETED**; after that, no further sharing.

**Example (share-chain user):**

```json
{
  "share_note": "My note.",
  "individual_status": "COMPLETED"
}
```

### DELETE

Only the **creator** can delete the entry.

---

## 3. Co-author approve

| Field    | Value |
|----------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/ActionableEntriesByID/<id>/co-author-approve/` |

**Body:** None.

**Effect:** Sets `approved_by_coauthor=True` and `final_Status=INPROCESS`. Only the assigned co_author can call.

**Success (200):** `{ "message": "Entry approved by co-author", "entry": { ... } }`

---

## 4. Share further

| Field    | Value |
|----------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/ActionableEntriesByID/<id>/share/` |

**Body:**

```json
{
  "share_with": "next_username",
  "note": "Optional note for this share."
}
```

**Rules:**

- Caller must be in the share chain.
- Caller’s share row `individual_status` is set to **INPROCESS**.
- A new share row is created for `share_with` with **PENDING**.
- Not allowed if any share row is **COMPLETED** or entry `final_Status` is **COMPLETED**.
- `share_with` must not already be in the chain.

**Success (200):** Full entry object with updated `share_chain`.

**Errors:**

- 400 – No further sharing (already Completed / final status Completed); or user already in chain.
- 403 – Caller not in share chain.
- 404 – Entry or user not found.

---

## 5. Co-author entries (list + detail)

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/ActionableEntriesCoAuthor/` |
| GET    | `{{baseurl}}/ActionableEntriesCoAuthor/<id>/` |
| PATCH  | `{{baseurl}}/ActionableEntriesCoAuthor/<id>/` |

**List:** Optional `?month=1`–`12`. Returns entries where current user is `co_author`.

**Detail:** Get or update one entry; allowed only if current user is the co_author.

---

## 6. Shared-with entries (list + detail)

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/ActionableEntriesSharedWith/` |
| GET    | `{{baseurl}}/ActionableEntriesSharedWith/<id>/` |
| PATCH  | `{{baseurl}}/ActionableEntriesSharedWith/<id>/` |

**List:** Optional `?month=1`–`12`. Returns entries where current user is in the **share chain** and `approved_by_coauthor=True`.

**Detail:** Get or update; allowed only if current user is in the share chain and entry is approved. PATCH accepts **share_note** and **individual_status** (same rules as in section 2: only last in chain can set COMPLETED).

---

## 7. Other endpoints (unchanged)

| Purpose                    | Method | URL |
|----------------------------|--------|-----|
| Add day entries            | POST   | `{{baseurl}}/addDayEntries/` |
| Get user entries           | GET    | `{{baseurl}}/getUserEntries/` |
| Change user entry status   | PATCH  | `{{baseurl}}/changeStatus/<user_entry_id>/` |
| Delete user entry          | DELETE | `{{baseurl}}/deleteEntry/<user_entry_id>/` |
| Get monthly schedule       | GET    | `{{baseurl}}/getMonthlySchedule/<user_id>/` |
| Add meeting head/subhead   | POST   | `{{baseurl}}/addMeetingHeadSubhead/` |
| Get functions & goals      | GET    | `{{baseurl}}/get_functions_and_actionable_goals/?function_name=<name>` |

---

## Quick reference – Actionable entries

| Purpose              | Method | URL |
|----------------------|--------|-----|
| List / create entries| GET / POST | `/ActionableEntries/` |
| Get / update / delete one | GET / PUT / PATCH / DELETE | `/ActionableEntriesByID/<id>/` |
| Co-author approve    | POST   | `/ActionableEntriesByID/<id>/co-author-approve/` |
| Share further        | POST   | `/ActionableEntriesByID/<id>/share/` |
| Co-author list/detail| GET / PATCH | `/ActionableEntriesCoAuthor/`, `/ActionableEntriesCoAuthor/<id>/` |
| Shared-with list/detail | GET / PATCH | `/ActionableEntriesSharedWith/`, `/ActionableEntriesSharedWith/<id>/` |

**TaskStatus values:** `PENDING`, `INPROCESS`, `COMPLETED` (confirm in your DB).
