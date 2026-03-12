# Quaterly Reports – API testing reference (Postman)

**Base URL:** `http://localhost:8000/` (or your server). QuaterlyReports routes are at the **root** (no prefix).  
**Auth:** All endpoints require a **logged-in user** (session/cookie).

This doc covers: user day entries (add/get/change/delete), monthly schedule (by department), meeting head/subhead, functions & goals, and actionable entries (list/create/share/co-author/shared-with).

---

## Status and share chain

- **Final status (creator):** `final_Status` on the entry. Default **PENDING** at creation. After **co-author approves** → **INPROCESS**. The creator can set **COMPLETED** **only after all share-chain users** have marked their **individual_status** as **COMPLETED** (or when there is no share chain).
- **Share chain:** Stored in `FunctionsEntriesShare`. First `share_with` and `shared_note` can be set by the creator at create. Others are added via **Share further**. Each row has: `shared_with`, `shared_note`, `shared_time`, `individual_status`. Entry creator text is `original_entry`; share-row text is `shared_note`.
- **Who shares further:** Anyone already in the share chain. When they share, their **individual_status** is set to **INPROCESS**. The **last** person in the chain (by `shared_time`) can set their **individual_status** to **COMPLETED** first. **After** the last user has set **COMPLETED**, any other share-chain user may change their own status from **Inprogress** to **Completed**.
- **No further sharing** when: any share row has status **COMPLETED**, or entry **final_Status** is **COMPLETED**.

## 1. List / Create actionable entries

| Field    | Value |
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
  "product": "Product A",
  // "final_Status": null
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
| product        | string | No       | **Full product name** (must exist in Product table). Omit or leave blank for no product. |
| final_Status   | string | No       | Default PENDING. |

**Success (201):** Created entry with `share_chain` (one item); response includes **product_name** (full product name or null). `co_author` and `share_with` are required on create.

---

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

## 6. Other endpoints (user entries, schedule, meeting head, functions & goals)

All below use **base URL** = root (e.g. `http://localhost:8000/`). QuaterlyReports routes are mounted at root. All require **logged-in user** (session/cookie).

### 6.1 Get monthly schedule (by department)

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/getMonthlySchedule/?department=<department_name>` |

**Query parameters:**

| Key        | Required | Description |
|------------|----------|-------------|
| department | **Yes**  | Department name (e.g. `Engineering`). Alternatively use `dept` instead of `department`. |
| month      | No       | Month name (e.g. `April`) – if omitted, current financial year’s month is used. |
| quater     | No       | Quarter (e.g. `Q1`) – required together with `month` when specifying a specific month. |

**Postman example:**

- URL: `http://localhost:8000/getMonthlySchedule/?department=Engineering`
- Optional: `http://localhost:8000/getMonthlySchedule/?department=Engineering&quater=Q1&month=April`

**Success (200):** Array of objects with `id`, `quater`, `financial_year`, `month`, `actual_month`, `Meeting-head`, `Sub-Meeting-head`, `sub-head-D1`, `sub-head-D2`, `sub-head-D3`.

---

### 6.2 Add day entries

| Field    | Value |
|----------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/addDayEntries/` |

**Headers:** `Content-Type: application/json`

**Body (example):**

```json
{
  "date": "2026-03-15",
  "month_quater_id": 1,
  "product": "Product A",
  "entries": [
    {
      "note": "Completed report review",
      "status": "Done"
    },
    {
      "note": "Follow-up meeting",
      "status": "Pending"
    }
  ]
}
```

| Key              | Type   | Required | Description |
|------------------|--------|----------|-------------|
| date             | string | **Yes**  | Date in YYYY-MM-DD. |
| month_quater_id  | int    | **Yes**  | ID of `Monthly_department_head_and_subhead` record. |
| product          | string | No       | **Full product name** (applies to all entries in this request). Must exist in Product table. Omit or leave blank for no product. |
| entries          | array  | **Yes**  | List of entry objects. |
| entries[].note   | string | **Yes**  | Entry note. |
| entries[].status | string | **Yes**  | Task status name (e.g. `Done`, `Pending`). |

**Success (201):** `{"message": "Entries created successfully", "created_entry_ids": [1, 2]}`.

---

### 6.3 Get user entries

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/getUserEntries/?username=<username>&quater=<Q>&month=<month>&department=<dept_name>` |

**Query parameters:**

| Key        | Required | Description |
|------------|----------|-------------|
| username   | **Yes**  | Username of the user whose entries to fetch. |
| quater     | **Yes**  | Quarter (e.g. `Q1`, `Q2`, `Q3`, `Q4`). |
| month      | **Yes**  | Month (e.g. `April`). |
| department | **Yes**  | Department name. |
| date       | No       | If provided, filter entries to this date (YYYY-MM-DD). |

**Postman example:**

- URL: `http://localhost:8000/getUserEntries/?username=jane&quater=Q1&month=April&department=Engineering`

**Success (200):** Array of entry objects. Each has: `id`, `note`, `meeting_head`, `meeting_sub_head`, `username`, `date`, `status`, `month_quater_id`, **`product_name`** (full product name or `null`).

---

### 6.4 Change user entry status

| Field    | Value |
|----------|--------|
| **Method** | `PATCH` |
| **URL**    | `{{baseurl}}/changeStatus/<user_entry_id>/` |

**Headers:** `Content-Type: application/json`

**Body (example):**

```json
{
  "change_Status_to": "Done"
}
```

| Key               | Type   | Required | Description |
|-------------------|--------|----------|-------------|
| change_Status_to  | string | **Yes**  | New status name (e.g. `Done`, `Pending`). |

**Postman example:**

- URL: `http://localhost:8000/changeStatus/42/`
- Body: `{"change_Status_to": "Done"}`

---

### 6.5 Delete user entry

| Field    | Value |
|----------|--------|
| **Method** | `DELETE` |
| **URL**    | `{{baseurl}}/deleteEntry/<user_entry_id>/` |

No body. Only the entry owner can delete.

**Postman example:**

- URL: `http://localhost:8000/deleteEntry/42/`

**Success (200):** `{"message": "entry deleted successfully"}`.

---

### 6.6 Add meeting head / subhead

| Field    | Value |
|----------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/addMeetingHeadSubhead/` |

**Headers:** `Content-Type: application/json`

**Body (example):**

```json
{
  "dept": "Engineering",
  "month": 1,
  "head": "Meeting Head Name",
  "sub_head": "Sub Head Name",
  "sub_d1": "Sub Head D1",
  "sub_d2": "Sub Head D2",
  "sub_d3": "Sub Head D3"
}
```

| Key       | Type   | Required | Description |
|-----------|--------|----------|-------------|
| dept      | string | **Yes**  | Department name. |
| month     | int    | **Yes**  | Month-of-quarter value (e.g. 1, 2, 3 for Q1). |
| head      | string | **Yes**  | Meeting head. |
| sub_head  | string | **Yes**  | Meeting sub-head. |
| sub_d1    | string | **Yes**  | Sub-head D1. |
| sub_d2    | string | **Yes**  | Sub-head D2. |
| sub_d3    | string | **Yes**  | Sub-head D3. |

**Success (200):** `{"Message": "added successfully"}`.

---

### 6.7 Get functions and actionable goals

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/get_functions_and_actionable_goals/?function_name=<name>` |

**Query parameters:**

| Key            | Required | Description |
|----------------|----------|-------------|
| function_name  | **Yes**  | Function name (case-insensitive). |

**Postman example:**

- URL: `http://localhost:8000/get_functions_and_actionable_goals/?function_name=Sales`

**Success (200):** Object with `function` and `functional_goals` (list of main goals and actionable goals with `actionable_id`, `purpose`, `grp_id`).

---

## Quick reference – All QuaterlyReports APIs (Postman)

**Base URL:** `http://localhost:8000/` (or your server root). All require **logged-in session**.

| Purpose                    | Method | URL | Body / Params |
|----------------------------|--------|-----|----------------|
| Get monthly schedule       | GET    | `/getMonthlySchedule/?department=<dept_name>` | Query: **department** (or **dept**); optional: **month**, **quater** |
| Add day entries            | POST   | `/addDayEntries/` | Body: `date`, `month_quater_id`, optional `product` (name, applies to all entries), `entries` (each: `note`, `status`) |
| Get user entries           | GET    | `/getUserEntries/?username=&quater=&month=&department=` | Query: **username**, **quater**, **month**, **department**; optional: **date** |
| Change user entry status   | PATCH  | `/changeStatus/<user_entry_id>/` | Body: `{"change_Status_to": "Done"}` |
| Delete user entry          | DELETE | `/deleteEntry/<user_entry_id>/` | No body |
| Add meeting head/subhead   | POST   | `/addMeetingHeadSubhead/` | Body: `dept`, `month`, `head`, `sub_head`, `sub_d1`, `sub_d2`, `sub_d3` |
| Get functions & goals     | GET    | `/get_functions_and_actionable_goals/?function_name=<name>` | Query: **function_name** |
| List / create actionable entries | GET / POST | `/ActionableEntries/` | POST: see section 1 |
| Get / update / delete one entry | GET / PUT / PATCH / DELETE | `/ActionableEntriesByID/<id>/` | PATCH: see section 2 |
| Share further              | POST   | `/ActionableEntriesByID/<id>/share/` | Body: `share_with`, optional `shared_note` |
| Co-author list, detail, approve | GET / PATCH | `/ActionableEntriesCoAuthor/`, `/ActionableEntriesCoAuthor/<id>/` | PATCH: e.g. `approved_by_coauthor`, `co_author_note` |
| Shared-with list/detail    | GET / PATCH | `/ActionableEntriesSharedWith/`, `/ActionableEntriesSharedWith/<id>/` | PATCH: `share_note`, `individual_status` |

**TaskStatus values (user entries):** e.g. `Done`, `Pending` (confirm in your DB).  
**Actionable entry status:** `PENDING`, `INPROCESS`, `COMPLETED`.
