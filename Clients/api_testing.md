# Clients API – Testing reference

**Base prefix:** `{{baseurl}}/clientsapi/`  
**Auth:** All endpoints require a logged-in user (session/cookie).  
**Access:** Profile and conversation endpoints are restricted to the profile **creator** or **members** only.

---

## 1. Products

**url:** `{{baseurl}}/clientsapi/products/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "id": 1, "name": "Product A" },
  { "id": 2, "name": "Product B" }
]
```
**notes:** Returns all products (id, name) for dropdowns. No query params.

---

## 2. Employees

**url:** `{{baseurl}}/clientsapi/employees/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "id": 1, "username": "user1" },
  { "id": 2, "username": "user2" }
]
```
**notes:** All users (id, username) for employee checkboxes.

---

## 3. Stages

**url:** `{{baseurl}}/clientsapi/stages/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "id": 1, "name": "Leads" },
  { "id": 2, "name": "Qualified" }
]
```
**notes:** Pipeline stages for status dropdown.

---

## 4. Profiles – List and create

**url:** `{{baseurl}}/clientsapi/profiles/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "id": 1,
    "company_name": "Acme Corp",
    "client_name": "John Doe",
    "client_contact": "",
    "representative_contact_number": "",
    "representative_name": "",
    "motive": "",
    "gst_number": "",
    "status_id": 1,
    "status_name": "Leads",
    "product_id": 1,
    "product_name": "Product A",
    "created_by": "admin",
    "members": ["Full Name 1"],
    "notes": [],
    "created_at": "16/03/2026 12:00:00",
    "updated_at": "16/03/2026 12:00:00"
  }
]
```
**notes:** Returns only profiles where the current user is **creator** or **member**. No query params.

---

**url:** `{{baseurl}}/clientsapi/profiles/`  
**method:** POST  
**body:**
```json
{
  "company_name": "Acme Corp",
  "client_name": "John Doe",
  "client_contact": "",
  "representative_contact_number": "",
  "representative_name": "",
  "motive": "Sales lead",
  "gst_number": "",
  "status_id": 1,
  "product_name": "Product A",
  "members": ["user1", "user2"]
}
```
**sample_response:**
```json
{ "id": 1, "message": "Client lead created" }
```
**notes:** `company_name` and `client_name` are required. `members` is optional array of usernames. Created by = logged-in user. 201 on success.

---

## 5. Profile – Detail, update, delete

**url:** `{{baseurl}}/clientsapi/profiles/<profile_id>/`  
**method:** GET  
**body:** None  
**sample_response:** Same shape as one item in the list (see §4).  
**notes:** 403 if user is not creator or member. 404 if profile not found.

---

**url:** `{{baseurl}}/clientsapi/profiles/<profile_id>/`  
**method:** PUT or PATCH  
**body:**
```json
{
  "company_name": "Acme Corp Updated",
  "client_name": "John Doe",
  "representative_name": "Jane",
  "members": ["user1"]
}
```
**sample_response:**
```json
{ "message": "Client lead updated" }
```
**notes:** 403 if not creator/member. Partial fields allowed for PATCH.

---

**url:** `{{baseurl}}/clientsapi/profiles/<profile_id>/`  
**method:** DELETE  
**body:** None  
**sample_response:**
```json
{ "message": "Client lead deleted" }
```
**notes:** 403 if not creator/member. 404 if profile not found.

---

## 6. Profile members

**url:** `{{baseurl}}/clientsapi/profiles/<profile_id>/members/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
["Full Name 1", "Full Name 2"]
```
**notes:** 403 if not creator/member. Returns display names of members.

---

## 7. Conversations – List and create

**url:** `{{baseurl}}/clientsapi/profiles/<profile_id>/conversations/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "id": 101,
    "note": "Had an introductory call.",
    "created_by": "john_doe",
    "created_at": "09/03/2026 15:30:00",
    "medium": "Calls"
  }
]
```
**notes:** 403 if not creator/member. `medium` is full name (Calls, Trial, Demand, Pitch) or null.

---

**url:** `{{baseurl}}/clientsapi/profiles/<profile_id>/conversations/`  
**method:** POST  
**body (single note):**
```json
{
  "note": "Explained pricing.",
  "medium": "Pitch"
}
```
**body (multiple notes):**
```json
{
  "notes": ["Note 1", "Note 2"],
  "medium": "Trial"
}
```
**sample_response (single):**
```json
{ "id": 123, "message": "Note added" }
```
**sample_response (multiple):**
```json
{ "ids": [201, 202], "message": "2 note(s) added" }
```
**notes:** `note` or `notes` required. `medium` optional: one of Calls, Trial, Demand, Pitch (case-insensitive). Invalid medium returns 400. 403 if not creator/member. POSTing with medium updates SalesStatistics for client product and today.

---

## 8. Conversation – Update and delete

**url:** `{{baseurl}}/clientsapi/profiles/<profile_id>/conversations/<note_id>/`  
**method:** PATCH  
**body:**
```json
{ "note": "Updated note text." }
```
**sample_response:**
```json
{ "message": "Note updated" }
```
**notes:** 403 if not creator/member. Only `note` is updatable.

---

**url:** `{{baseurl}}/clientsapi/profiles/<profile_id>/conversations/<note_id>/`  
**method:** DELETE  
**body:** None  
**sample_response:**
```json
{ "message": "Note deleted" }
```
**notes:** 403 if not creator/member. 404 if note not found.
