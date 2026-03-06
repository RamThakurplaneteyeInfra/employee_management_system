# Quaterly Reports – Actionable Entries APIs (Testing reference)

<!-- Base URL: `http://localhost:8000` (or your server).  
Endpoints below are at the **root** (e.g. `/ActionableEntries/`).  
All require **logged-in user** (session/cookie auth).

--- -->

## Status and share chain

- **Final status (creator):** `final_Status` on the entry. Default **PENDING** at creation. After **co-author approves** → **INPROCESS**. The creator can set **COMPLETED** **only after all share-chain users** have marked their **individual_status** as **COMPLETED** (or when there is no share chain).
- **Share chain:** Stored in `FunctionsEntriesShare`. First `share_with` and `shared_note` can be set by the creator at create. Others are added via **Share further**. Each row has: `shared_with`, `shared_note`, `shared_time`, `individual_status`. Entry creator text is `original_entry`; share-row text is `shared_note`.
- **Who shares further:** Anyone already in the share chain. When they share, their **individual_status** is set to **INPROCESS**. The **last** person in the chain (by `shared_time`) can set their **individual_status** to **COMPLETED** first. **After** the last user has set **COMPLETED**, any other share-chain user may change their own status from **Inprogress** to **Completed**.
- **No further sharing** when: any share row has status **COMPLETED**, or entry **final_Status** is **COMPLETED**.

## 1. List / Create actionable entries

<!-- | Field    | Value |
|----------|--------|
| **Method** | `GET` (list) \| `POST` (create) |
| **URL**    | `{{baseurl}}/ActionableEntries/` |

### GET – List

**Query (optional):** `username`, `month`. If not superuser, only own entries (and month) are allowed.

**Success (200):** Array of entry objects. Each entry has `creator_name`, `co_author_name` (full names from Profile), `original_entry` (creator’s entry text), and `share_chain` (array of `{ id, actionable_entry, shared_with_name, shared_note, shared_time, status_name }`). User references return full name from Profile; status is `status_name` only.

### POST – Create

**Headers:** `Content-Type: application/json`

**Body (example):**

```json
{
  "goal": 1,
  "co_author": "jane",
  "share_with": "bob",
  "shared_note": "Note for the first share.",
  "date": "2026-03-15",
  "original_entry": "Entry note.",
  "final_Status": null
}
```

| Key            | Type   | Required | Description |
|----------------|--------|----------|-------------|
| goal           | int    | **Yes**  | ActionableGoals PK (Goal_id). Required when creating an entry. |
| co_author      | string | **Yes**  | Username of co-author. Required when creating an entry. |
| share_with     | string | **Yes**  | Username of **first** share recipient (creates first row in share chain). Required when creating an entry. |
| shared_note    | string | No       | Note for the first share (stored in `FunctionsEntriesShare.shared_note`). |
| date           | string | Yes      | YYYY-MM-DD. |
| original_entry | string | Yes      | Creator’s entry text. |
| final_Status   | string | No       | Default PENDING. |

**Success (201):** Created entry with `share_chain` (one item; `co_author` and `share_with` are required on create).

--- -->

## 2. Get / Update / Delete one entry

| Field    | Value |
|----------|--------|
| **Method** | `GET` \| `PUT` \| `PATCH` \| `DELETE` |
| **URL**    | `{{baseurl}}/ActionableEntriesByID/<id>/` |

**Visibility:** Creator, co_author, or any user in `share_chain` (and `approved_by_coauthor=True`).

### PATCH – Update (creator / co_author)

Creator or co_author can update entry fields (e.g. `original_entry`, `final_Status`, `co_author`, `co_author_note`). **Creator cannot set `final_Status` to INPROCESS**—that only changes when the co_author approves. Creator can set `final_Status` to **COMPLETED** **only after all share-chain users** have marked their **individual_status** as **COMPLETED**; otherwise the API returns a validation error. **Only the co_author** can set or update **`co_author_note`** (details to the creator before or after approval).

### PATCH – Update (share-chain user)

If the current user is in the share chain (and not creator/co_author), only these body fields are applied:

- **share_note** – update this user’s share row `shared_note`.
- **individual_status** – set this user’s share row status (e.g. `"COMPLETED"`). The **last** person in the chain (by `shared_time`) must set **COMPLETED** first. **After** the last user has set **COMPLETED**, any other share-chain user may change their status from **Inprogress** to **Completed**.

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

## 3. Share further

| Field    | Value |
|----------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/ActionableEntriesByID/<id>/share/` |

**Body:**

```json
{
  "share_with": "next_username",
  "shared_note": "Optional note for this share (stored in share chain as shared_note)."
}
```

| Key         | Type   | Required | Description |
|-------------|--------|----------|-------------|
| share_with  | string | **Yes**  | Username of the next user in the share chain. |
| shared_note | string | No       | Note for this share (stored in `FunctionsEntriesShare.shared_note`). |

**Rules:**

- Caller must be in the share chain.
- Caller’s share row `individual_status` is set to **INPROCESS**.
- A new share row is created for `share_with` with **PENDING**; body `shared_note` is stored in that row’s `shared_note` field.
- Not allowed if any share row is **COMPLETED** or entry `final_Status` is **COMPLETED**.
- `share_with` must not already be in the chain.

**Success (200):** Full entry object with updated `share_chain`.

**Errors:**

- 400 – No further sharing (already Completed / final status Completed); or user already in chain.
- 403 – Caller not in share chain.
- 404 – Entry or user not found.

---

## 4. Co-author entries (list + detail + approval)

Single endpoint for fetching co-author entries and changing approval status.

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/ActionableEntriesCoAuthor/` |
| GET    | `{{baseurl}}/ActionableEntriesCoAuthor/<id>/` |
| PATCH  | `{{baseurl}}/ActionableEntriesCoAuthor/<id>/` |

**List (GET):** Optional `?month=1`–`12`. Returns entries where current user is `co_author`.

**Detail (GET):** One entry; allowed only if current user is the co_author.

**Update / approve (PATCH):** Co-author can update entry fields, set **`co_author_note`** (message to the creator, before or after approval), or **approve** by sending `{"approved_by_coauthor": true}`. Approval sets `approved_by_coauthor=True` and `final_Status=INPROCESS`. Only the assigned co_author can set approval and `co_author_note`. Responses include `co_author_note`.

---

## 5. Shared-with entries (list + detail)

| Method | URL |
|--------|-----|
| GET    | `{{baseurl}}/ActionableEntriesSharedWith/` |
| GET    | `{{baseurl}}/ActionableEntriesSharedWith/<id>/` |
| PATCH  | `{{baseurl}}/ActionableEntriesSharedWith/<id>/` |

**List:** Optional `?month=1`–`12`. Returns entries where current user is in the **share chain** and `approved_by_coauthor=True`.

**Detail:** Get or update; allowed only if current user is in the share chain and entry is approved. PATCH accepts **share_note** and **individual_status** (same rules as in section 2: last in chain sets COMPLETED first, then other share-chain users may set their status to COMPLETED).

---

## 6. Other endpoints (unchanged)

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
| Share further        | POST   | `/ActionableEntriesByID/<id>/share/` |
| Co-author list, detail, approve | GET / PATCH | `/ActionableEntriesCoAuthor/`, `/ActionableEntriesCoAuthor/<id>/` |
| Shared-with list/detail | GET / PATCH | `/ActionableEntriesSharedWith/`, `/ActionableEntriesSharedWith/<id>/` |

**TaskStatus values:** `PENDING`, `INPROCESS`, `COMPLETED` (confirm in your DB).
