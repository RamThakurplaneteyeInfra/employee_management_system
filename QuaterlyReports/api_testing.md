# Quaterly Reports API – Testing reference

**Base prefix:** `{{baseurl}}/` (QuaterlyReports urls are mounted at root.)  
**Auth:** All endpoints require a logged-in user unless noted.  
**Content-Type:** `application/json` for JSON bodies.

---

## 1. Monthly schedule and entries

### getMonthlySchedule

**url:** `{{baseurl}}/getMonthlySchedule/`  
**method:** GET  
**body:** None  
**query params:** `department` (or `dept`) required. Optional: `month`, `quater` (if omitted, current financial year/quarter used).  
**sample_response:**
```json
[
  {
    "id": 1,
    "quater": "Q1",
    "financial_year": "2025-2026",
    "month": 1,
    "actual_month": "April",
    "Meeting-head": "Sales Review",
    "Sub-Meeting-head": "Regional",
    "sub-head-D1": "",
    "sub-head-D2": "",
    "sub-head-D3": ""
  }
]
```
**notes:** 400 if department missing; 404 if department not found or no schedule.

---

### addDayEntries

**url:** `{{baseurl}}/addDayEntries/`  
**method:** POST  
**body:**
```json
{
  "date": "2026-03-15",
  "month_quater_id": 1,
  "product": "Product A",
  "entries": [
    { "note": "Completed task X", "status": "COMPLETED" },
    { "note": "In progress Y", "status": "INPROCESS" }
  ]
}
```
**sample_response:**
```json
{
  "message": "Entries created successfully",
  "created_entry_ids": [101, 102]
}
```
**notes:** Superuser cannot create entries. Required: date, entries, month_quater_id. Each entry: note, status (task status name). product optional (Product name). 201 on success; 404 for invalid month_quater_id or product.

---

### getUserEntries

**url:** `{{baseurl}}/getUserEntries/`  
**method:** GET  
**body:** None  
**query params:** `username` required; `date`, `quater`, `month`, `department` as needed.  
**sample_response:** Array of user entry objects (filtered by query).  
**notes:** Caller must be superuser or the same username. 400 if username missing; 403 if not authorised.

---

### changeStatus

**url:** `{{baseurl}}/changeStatus/<user_entry_id>/`  
**method:** PATCH  
**body:**
```json
{ "change_Status_to": "COMPLETED" }
```
**sample_response:**
```json
{ "message": "Status Changed to COMPLETED" }
```
**notes:** Status must match TaskStatus (e.g. PENDING, INPROCESS, COMPLETED). 404 if entry not found.

---

### deleteEntry

**url:** `{{baseurl}}/deleteEntry/<user_entry_id>/`  
**method:** DELETE  
**body:** None  
**sample_response:**
```json
{ "message": "entry deleted successfully" }
```
**notes:** Only entry owner can delete. 403 if not owner; 404 if entry not found.

---

### addMeetingHeadSubhead

**url:** `{{baseurl}}/addMeetingHeadSubhead/`  
**method:** POST  
**body:**
```json
{
  "dept": "Engineering",
  "month": 1,
  "head": "Meeting Head",
  "sub_head": "Sub head",
  "sub_d1": "",
  "sub_d2": "",
  "sub_d3": ""
}
```
**sample_response:**
```json
{ "Message": "added successfully" }
```
**notes:** Creates/updates monthly department head and subhead. 400 on error.

---

## 2. Functions and actionable goals

### get_functions_and_actionable_goals

**url:** `{{baseurl}}/get_functions_and_actionable_goals/`  
**method:** GET  
**body:** None  
**query params:** `function_name` required.  
**sample_response:**
```json
{
  "function": "Development",
  "functional_goals": [
    {
      "functional_id": 1,
      "main_goal": "Deliver features",
      "actionable_goals": [
        { "actionable_id": 1, "purpose": "Sprint delivery", "grp_id": "G1" }
      ]
    }
  ]
}
```
**notes:** 400 if function_name missing; 404 if function not found.

---

## 3. Actionable entries (FunctionsEntries)

### ActionableEntries – List or create

**url:** `{{baseurl}}/ActionableEntries/`  
**method:** GET  
**body:** None  
**query params:** Optional `username` (superuser only), `month` (1–12). Without username/month: current user's entries for current month (or specified month).  
**sample_response:** Array of actionable entry objects (Creator, co_author, product, date, share_chain, etc. per FunctionsEntriesSerializer).  
**notes:** Visibility: creator; co_author; or in share_chain and approved_by_coauthor. EntryPermission applied.

---

**url:** `{{baseurl}}/ActionableEntries/`  
**method:** POST  
**body:** Fields per FunctionsEntriesSerializer (Creator set from request.user).  
**sample_response:** Created entry (full object). 201.  
**notes:** EntryPermission applied. 400 on validation error.

---

### ActionableEntriesByID – Detail, update, delete

**url:** `{{baseurl}}/ActionableEntriesByID/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single entry with share_chain.  
**notes:** Visible only to creator, co_author, or approved share_chain. 404 if not found or not visible.

---

**url:** `{{baseurl}}/ActionableEntriesByID/<id>/`  
**method:** PUT or PATCH  
**body:** For creator/co_author: full or partial entry fields. For share_chain user only: share_note, individual_status (COMPLETED only by last in chain first).  
**sample_response:** Updated entry.  
**notes:** Only creator can delete. Share-chain user can update only their share row (share_note, individual_status). 403 if only last in chain can set COMPLETED first. 404 if not found.

---

**url:** `{{baseurl}}/ActionableEntriesByID/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:**
```json
{ "message": "entry deleted successfully" }
```
**notes:** Creator only. 202 on success; 403 if not creator.

---

### ActionableEntriesByID share – Share further

**url:** `{{baseurl}}/ActionableEntriesByID/<id>/share/`  
**method:** POST  
**body:**
```json
{ "share_with": "username", "shared_note": "Please review" }
```
**sample_response:** Full entry object with updated share_chain.  
**notes:** Caller must be in share chain; their status set to Inprogress; new user added with Pending. Not allowed when entry or chain is COMPLETED. 400 if user already in chain; 403 if caller not in chain; 404 if entry or user not found.

---

## 4. Co-author entries

### ActionableEntriesCoAuthor – List

**url:** `{{baseurl}}/ActionableEntriesCoAuthor/`  
**method:** GET  
**body:** None  
**query params:** Optional `month` (1–12); default current month.  
**sample_response:** Array of actionable entries where co_author = current user.  
**notes:** EntryPermission applied.

---

### ActionableEntriesCoAuthor – Detail and approve

**url:** `{{baseurl}}/ActionableEntriesCoAuthor/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single entry.  
**notes:** Only co-author. 404 if not co-author.

---

**url:** `{{baseurl}}/ActionableEntriesCoAuthor/<id>/`  
**method:** PATCH  
**body:**
```json
{ "approved_by_coauthor": true }
```
**sample_response:** Updated entry.  
**notes:** Co-author can set approved_by_coauthor so shared_with users see the entry. 404 if not co-author.

---

## 5. Shared-with entries

### ActionableEntriesSharedWith – List

**url:** `{{baseurl}}/ActionableEntriesSharedWith/`  
**method:** GET  
**body:** None  
**query params:** Optional `month` (1–12).  
**sample_response:** Array of entries where current user is in share_chain and approved_by_coauthor = true.  
**notes:** EntryPermission applied.

---

### ActionableEntriesSharedWith – Detail and update

**url:** `{{baseurl}}/ActionableEntriesSharedWith/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single entry.  
**notes:** Only if in share_chain and approved. 403 if not approved yet; 404 if not in chain.

---

**url:** `{{baseurl}}/ActionableEntriesSharedWith/<id>/`  
**method:** PATCH  
**body:**
```json
{ "share_note": "Done", "individual_status": "COMPLETED" }
```
**sample_response:** Updated entry.  
**notes:** Share-chain user can update only their share_note and individual_status. COMPLETED: only last in chain (by shared_time) can set first; then others may set. 403 if not last when setting COMPLETED first; 404 if not in chain.
