# Accounts API – Testing reference

**Base prefix:** `{{baseurl}}/accounts/`  
**Auth:** Most endpoints require a logged-in user (session/cookie); login/logout and some filters are unauthenticated. Admin-only endpoints noted.  
**Content-Type:** `application/json` for JSON bodies; `application/x-www-form-urlencoded` or `multipart/form-data` for form-based endpoints.

---

## 1. Session and home

### home

**url:** `{{baseurl}}/accounts/`  
**method:** GET  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** Placeholder home; no body.

---

### login

**url:** `{{baseurl}}/accounts/login/`  
**method:** POST  
**body:**
```json
{ "username": "0001", "password": "your_password" }
```
**sample_response:**
```json
{
  "messege": "You are logged in",
  "username": "0001",
  "Role": "Admin",
  "department": "Engineering"
}
```
**notes:** Creates session; single-device: any existing session for this user is expired first. 400 if username/password missing or invalid.

---

### logout

**url:** `{{baseurl}}/accounts/logout/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{ "messege": "Logout successfully 0001" }
```
**notes:** Logged-in user only; session flushed.

---

### sessiondata

**url:** `{{baseurl}}/accounts/sessiondata/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{
  "expiray-age": 1209600,
  "expiray-date": "2026-03-23T...",
  "accessed": true,
  "is_empty": false
}
```
**notes:** Logged-in user only. Session expiry and metadata.

---

## 2. Filters (dropdowns)

### getBranch

**url:** `{{baseurl}}/accounts/getBranch/`  
**method:** GET  
**body:** None  
**query params:** Optional `Role` — if MD or Admin returns `[{}]`; otherwise all branches.  
**sample_response:**
```json
[{ "branch_name": "Mumbai" }, { "branch_name": "Delhi" }]
```
**notes:** Used for branch dropdown by role.

---

### getRoles

**url:** `{{baseurl}}/accounts/getRoles/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[{ "role_name": "Admin" }, { "role_name": "MD" }, { "role_name": "Employee" }]
```
**notes:** All roles except role_id=1.

---

### getDesignations

**url:** `{{baseurl}}/accounts/getDesignations/`  
**method:** GET  
**body:** None  
**query params:** Optional `Role`.  
**sample_response:**
```json
[{ "designation": "Developer" }, { "designation": "Manager" }]
```
**notes:** All designations (or filtered by role if supported).

---

### getDepartmentsandFunctions

**url:** `{{baseurl}}/accounts/getDepartmentsandFunctions/`  
**method:** GET  
**body:** None  
**query params:** Optional `Role` — if Admin or MD returns empty Departments/functions.  
**sample_response:**
```json
{
  "Departments": ["Engineering", "HR"],
  "functions": ["Development", "Testing"]
}
```
**notes:** Used for department and function dropdowns.

---

### getTeamleads

**url:** `{{baseurl}}/accounts/getTeamleads/`  
**method:** GET  
**body:** None  
**query params:** Optional `Role` — one of Employee, Intern to get team leads; otherwise returns `[{}]`.  
**sample_response:**
```json
[{ "Name": "Lead One", "Employee_id": "lead1" }]
```
**notes:** Team leads for assignment dropdown. 404 if invalid.

---

## DM targets and work scoring

### DM scoring targets (MD-managed)

**url:** `{{baseurl}}/accounts/dm-scoring-targets/?year=2026&month=7`  
**method:** GET  
**notes:** MD/HR can view. Returns DM employees and effective targets for the month (digital_media_target_count, digital_content_target_count).

**url:** `{{baseurl}}/accounts/dm-scoring-targets/<employee_id>/?year=2026&month=7`  
**method:** GET, PUT, PATCH  
**notes:** GET: MD/HR view. PUT/PATCH: MD only. Body fields: `digital_media_target_count`, `digital_content_target_count`.

---

### DM work entries (submit + approve)

**url:** `{{baseurl}}/accounts/dm-work-entries/`  
**method:** GET, POST  
**POST body:**
```json
{ "title": "Post title", "description": "Details...", "content_type": "digital_media" }
```
**notes:** Only DM employees can POST (creates `pending`). GET: DM sees own entries; MD can see all (optional `?employee=<username>`). Use `?year=&month=` to filter by created_at.

**url:** `{{baseurl}}/accounts/dm-work-entries/<id>/approve/`  
**method:** PATCH  
**body:**
```json
{ "status": "approved" }
```
**notes:** MD only. Status must be `approved` or `rejected`. Only `approved` entries count for scoring.

---

### DM work points

**url:** `{{baseurl}}/accounts/dm-work-entries/points/?year=2026&month=7`  
**method:** GET  
**notes:** Returns DM work scoring breakdown (main_score, monthly_bonus, total_points). Optional `?employee=<username>` for HR/MD.

---

## 3. Employee (self and list)

### employee dashboard

**url:** `{{baseurl}}/accounts/employee/dashboard/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "Employee_id": "0001",
    "Email_id": "admin@example.com",
    "Date_of_birth": "2020-02-02",
    "Date_of_join": "2020-02-04",
    "Name": "Jadhav",
    "Photo_link": null,
    "role": "Admin",
    "designation": null,
    "branch": null,
    "department": null,
    "functions": []
  }
]
```
**notes:** Logged-in user's profile. Admin/MD get minimal fields; others get designation, branch, department, functions.

---

### employees (all)

**url:** `{{baseurl}}/accounts/employees/`  
**method:** GET  
**body:** None  
**sample_response:** Array of employee objects with Employee_id, Name, Role, Branch, Designation, Date_of_birth, Date_of_join, Number_of_days_from_joining, Email_id, etc.  
**notes:** All employees; ordered by Name.

---

### updateUsername

**url:** `{{baseurl}}/accounts/updateUsername/<username>/`  
**method:** POST  
**body:** Form: `new_username=<new_value>`.  
**sample_response:** Plain text "username updated".  
**notes:** Updates user's username. 400/500 on error.

---

## 4. Admin-only (profile and user management)

### updateProfile

**url:** `{{baseurl}}/accounts/admin/updateProfile/<username>/`  
**method:** POST  
**body:** JSON or form: Name, Role, Email_id, Designation, Date_of_join, Date_of_birth, Branch, Department, Teamlead, Functions (array). Required: Name, Role, Email_id, Date_of_join, Date_of_birth.  
**sample_response:**
```json
{ "messege": "user details update successfully" }
```
**notes:** Admin only. 404 if user not found; 400 if validation fails.

---

### createEmployeeLogin

**url:** `{{baseurl}}/accounts/admin/createEmployeeLogin/`  
**method:** POST  
**body:** Form or multipart: Employee_id, password, Name, Role, Email_id, Designation, Date_of_join, Date_of_birth, Branch (optional), Photo_link (file, optional), Department, Teamlead, Functions (list). Role required; Branch/Designation/Department/Teamlead/Functions optional per logic.  
**sample_response:**
```json
{ "messege": "user profile created successfully" }
```
**notes:** Superuser, or Profile role Admin/MD/HR. HR cannot create Admin/MD/HR roles (403). Other admin endpoints remain superuser-only. Creates User and Profile. 400/403/404/500 on error.

---

### viewEmployee

**url:** `{{baseurl}}/accounts/admin/viewEmployee/<username>/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "Employee_id": "0001",
    "Email_id": "admin@example.com",
    "Designation": "Developer",
    "Date_of_birth": "2020-02-02",
    "Date_of_join": "2020-02-04",
    "Branch": "Mumbai",
    "Name": "Jadhav",
    "Photo_link": null,
    "Role": "Admin",
    "Functions": ["Dev", "QA"]
  }
]
```
**notes:** Admin only. 404 if user not found.

---

### deleteEmployee

**url:** `{{baseurl}}/accounts/admin/deleteEmployee/<username>/`  
**method:** DELETE  
**body:** None  
**sample_response:**
```json
{ "message": "user deleted successfully" }
```
**notes:** Admin only. 404 if user not found.

---

### changePassword

**url:** `{{baseurl}}/accounts/admin/changePassword/<username>/`  
**method:** PATCH  
**body:**
```json
{ "new_password": "new_secret" }
```
**sample_response:**
```json
{ "messege": "Password is changed to new_secret" }
```
**notes:** Admin only. 404 if user not found; 400 if password empty.

---

### changePhoto

**url:** `{{baseurl}}/accounts/admin/changePhoto/<username>/`  
**method:** POST  
**body:** Multipart: `Photo_link` (file).  
**sample_response:**
```json
{ "messege": "Jadhav's Photo updated successfully" }
```
**notes:** Admin only. 400 if no file; 404 if user not found.

---

### FetchPhoto

**url:** `{{baseurl}}/accounts/admin/FetchPhoto/<username>/`  
**method:** GET  
**body:** None  
**sample_response:** Image bytes with appropriate Content-Type, or `{"image": null}` if no photo.  
**notes:** Admin only. 404 if user not found.

---

## 5. Leave applications (DRF ViewSet)

**Base:** `{{baseurl}}/accounts/leave-applications/`

### List leave applications

**url:** `{{baseurl}}/accounts/leave-applications/`  
**method:** GET  
**body:** None  
**sample_response:** Array of leave application objects (id, applicant_name, team_lead_name, alternative_name, start_date, duration_of_days, leave_subject, reason, note, leave_type_name, half_day_slots, team_lead_approval_status, hr_approval_status, md_approval_status, admin_approval_status, is_emergency, application_date, applied_at, approved_by_MD_at).  
**notes:** Authenticated. Names from Profile; no FK ids in response.

---

### Retrieve leave application

**url:** `{{baseurl}}/accounts/leave-applications/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single leave application (same shape as list).  
**notes:** 404 if not found.

---

### Create leave application (regular)

**url:** `{{baseurl}}/accounts/leave-applications/`  
**method:** POST  
**body:**
```json
{
  "leave_type": "Full_day",
  "start_date": "2026-03-20",
  "duration_of_days": 2,
  "leave_subject": "Personal",
  "reason": "Family event",
  "note": "",
  "half_day_slots": null,
  "alternative": "colleague_username"
}
```
**sample_response:** Created application (same shape as list). 201.  
**notes:** Applicant = logged-in user. leave_type by name (e.g. Full_day, Half_day). Full_day: validates remaining leaves; Half_day: validates half_day_slots. Approval hierarchy set by role (Team lead → HR/Admin → MD). MD applicant auto-approved and used_leaves incremented.

---

### Emergency leave (HR only)

**url:** `{{baseurl}}/accounts/leave-applications/emergency/`  
**method:** POST  
**body:**
```json
{
  "applicant": "username",
  "leave_type": "Full_day",
  "start_date": "2026-03-20",
  "duration_of_days": 1,
  "leave_subject": "Emergency",
  "reason": "Medical",
  "note": ""
}
```
**sample_response:** Created emergency application (same shape). 201.  
**notes:** HR only. Emergency quota (10% of total_leaves) enforced; all approvers set to Approved; used_leaves and emergency_leaves updated.

---

### Update leave application

**url:** `{{baseurl}}/accounts/leave-applications/<id>/`  
**method:** PUT or PATCH  
**body:** Allowed fields per LeaveApplicationUpdateSerializer (e.g. team_lead_approval, HR_approval, admin_approval, MD_approval, approved_by_MD_at).  
**sample_response:** Updated application.  
**notes:** Role-based: team lead can set team_lead_approval; HR can set HR_approval; Admin can set admin_approval; MD can set MD_approval and approved_by_MD_at. When MD approves non-emergency, used_leaves incremented. 404 if not found.

---

### Delete leave application

**url:** `{{baseurl}}/accounts/leave-applications/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if not found.

---

### Leave summary

**url:** `{{baseurl}}/accounts/leave-applications/summary/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{
  "total_leaves": 24,
  "used_leaves": 5,
  "remaining_leaves": 19,
  "remaining_emergency_leave": 2
}
```
**notes:** Logged-in user's LeaveSummary balance.

---

### View history (my applications)

**url:** `{{baseurl}}/accounts/leave-applications/view_history/`  
**method:** GET  
**body:** None  
**sample_response:** Array of leave applications where applicant = current user.  
**notes:** Same shape as list.

---

### Approval tab

**url:** `{{baseurl}}/accounts/leave-applications/approval/`  
**method:** GET  
**body:** None  
**sample_response:** Array of leave applications for current user's approval tab (default: sticky involvement history).
**notes:** Default `?status=all` — sequential first-show, rows **stay** after approve/reject with status fields (`team_lead_approval_status`, `hr_approval_status`, `md_approval_status`, etc.). Cover person: on submit. Team lead: after alternative responds (if any). HR: once `HR_approval` rail exists. MD: once `MD_approval` rail exists. Use `?status=pending` for action queue only (row drops after you act). Optional pagination below.

**pagination (optional, backward-compatible):** `?limit=20&offset=0` — if neither `limit` nor `offset` is sent, response is a plain array (legacy). If either is sent:

```json
{
  "items": [ /* leave application objects */ ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "next_offset": 20,
    "prev_offset": null,
    "has_next": true,
    "has_prev": false,
    "total": 45
  }
}
```

Default `limit` 30, max 100.

**applied_at:** IST datetime string (`DD/MM/YYYY HH:MM:SS`) for exact submission time. `application_date` remains date-only (`YYYY-MM-DD`) for backward compatibility. Legacy rows: `applied_at` set to midnight IST on `application_date` (migration 0059). New rows: real submit time from `auto_now_add`.

---

### On leave (MD-approved, absent on a day)

**url:** `{{baseurl}}/accounts/leave-applications/on-leave/`  
**method:** GET  
**query:** `date=YYYY-MM-DD` (optional; default today). `limit` / `offset` optional (same pagination as approval).  
**notes:** Only `MD_approval_status = Approved` and the given date falls within `start_date` … `end_date` (from `duration_of_days`). Each item includes `applicant_role` from Profile (e.g. Intern, Employee, TeamLead, HR, Admin, MD). HR / Admin / MD / superuser: all employees; Team lead: their team only. Others: 403.

**sample_response (no pagination):**
```json
{
  "date": "2026-06-03",
  "items": [
    {
      "id": 42,
      "applicant_name": "John Doe",
      "applicant_username": "200012",
      "applicant_role": "Employee",
      "start_date": "2026-06-03",
      "end_date": "2026-06-04",
      "duration_of_days": 2.0,
      "leave_type_name": "Full_day",
      "leave_subject": "Personal",
      "md_approval_status": "Approved",
      "approved_by_MD_at": "02/06/2026 14:30:00",
      "half_day_slots": null,
      "short_leave_start_time": null
    }
  ]
}
```
