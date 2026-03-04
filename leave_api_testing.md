# Leave APIs – Testing reference

Base URL: `http://localhost:8000` (or your server).  
All endpoints under `/accounts/leave-applications/` require **logged-in user** (session/cookie auth).  
Use the same session as for other accounts APIs (e.g. after `POST /accounts/login/`).

---

## 1. Create leave application (self)

Apply for leave as the logged-in user. Remaining-leaves balance is validated. Approval chain is set by role (TeamLead → HR → MD, or Admin → HR → MD, etc.). `team_lead` is auto-filled from Profile.

| Field    | Value |
|----------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/` |

**Headers**

- `Content-Type: application/json`

**Body** – raw JSON

```json
{
  "start_date": "2026-03-20",
  "duration_of_days": 2,
  "live_subject": "Personal leave",
  "reason": "Family event.",
  "leave_type": 1,
  "half_day_slots": null,
  "is_emergency": false
}
```

| Key               | Type    | Required | Description |
|-------------------|---------|----------|-------------|
| start_date        | string  | Yes      | Date (YYYY-MM-DD). |
| duration_of_days  | integer | Yes      | Number of days (≥ 1). |
| live_subject      | string  | Yes      | Short subject. |
| reason            | string  | Yes      | Leave reason. |
| leave_type        | int     | Yes      | PK of LeaveTypes (e.g. 1 = Full_day, 2 = Half_day). |
| half_day_slots    | string  | No       | `"First_Half"` or `"Second_Half"` when leave_type is Half_day; null for Full_day. |
| is_emergency      | boolean | No       | Default `false`. |

**Success response** – `201 Created`

```json
{
  "id": 1,
  "applicant": 1,
  "applicant_username": "john",
  "team_lead": 2,
  "team_lead_username": "jane_lead",
  "start_date": "2026-03-20",
  "duration_of_days": 2,
  "live_subject": "Personal leave",
  "reason": "Family event.",
  "leave_type": 1,
  "leave_type_name": "Full_day",
  "half_day_slots": null,
  "team_lead_approval": 2,
  "team_lead_approval_status": "Pending",
  "HR_approval": 2,
  "hr_approval_status": "Pending",
  "MD_approval": 2,
  "md_approval_status": "Pending",
  "admin_approval": null,
  "admin_approval_status": null,
  "is_emergency": false,
  "application_date": "2026-03-10",
  "approved_by_MD_at": null
}
```

**Error examples**

- `400` – Validation (e.g. missing field, invalid date).
- `400` – `{"non_field_errors": ["Insufficient leave balance. Remaining: 2, requested: 5."]}`

---

## 2. Create emergency leave (HR only)

HR creates leave on behalf of any user. No remaining-leaves check. Team lead approval is set to Approved; HR_approval is chosen; MD stays Pending.

| Field    | Value |
|----------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/emergency/` |

**Headers**

- `Content-Type: application/json`

**Body** – raw JSON

```json
{
  "applicant": 3,
  "start_date": "2026-03-22",
  "duration_of_days": 1,
  "live_subject": "Emergency",
  "reason": "Medical.",
  "leave_type": 1,
  "half_day_slots": null,
  "hr_approval_status": "Approved"
}
```

| Key               | Type   | Required | Description |
|-------------------|--------|----------|-------------|
| applicant         | int    | Yes      | User ID (auth_user) of the employee. |
| start_date        | string | Yes      | YYYY-MM-DD. |
| duration_of_days  | int    | Yes      | ≥ 1. |
| live_subject      | string | Yes      | Subject. |
| reason            | string | Yes      | Reason. |
| leave_type        | int    | Yes      | LeaveTypes PK. |
| half_day_slots    | string | No       | `"First_Half"` / `"Second_Half"` or null. |
| hr_approval_status| string | No       | `"Approved"`, `"Pending"`, or `"Rejected"`. Default `"Approved"`. |

**Success response** – `201 Created` (same shape as in section 1, with `is_emergency: true`).

**Error examples**

- `403` – User is not HR.
- `400` – Validation errors.

---

## 3. View history (my applications)

Logged-in user’s own leave applications.

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/view_history/` |

**Headers**

- None beyond session cookie.

**Body**

- None.

**Success response** – `200 OK`

```json
[
  {
    "id": 1,
    "applicant": 1,
    "applicant_username": "john",
    "team_lead": 2,
    "team_lead_username": "jane_lead",
    "start_date": "2026-03-20",
    "duration_of_days": 2,
    "live_subject": "Personal leave",
    "reason": "Family event.",
    "leave_type": 1,
    "leave_type_name": "Full_day",
    "half_day_slots": null,
    "team_lead_approval": 2,
    "team_lead_approval_status": "Pending",
    "HR_approval": 2,
    "hr_approval_status": "Pending",
    "MD_approval": 2,
    "md_approval_status": "Pending",
    "admin_approval": null,
    "admin_approval_status": null,
    "is_emergency": false,
    "application_date": "2026-03-10",
    "approved_by_MD_at": null
  }
]
```

---

## 4. Approval tab – Team lead

Applications where the current user is the team lead (multiple team leads supported).

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/approval_teamlead/` |

**Headers**

- Session cookie.

**Body**

- None.

**Success response** – `200 OK`

Array of leave application objects (same structure as in section 3). Empty array `[]` if the user is not a team lead for any application.

---

## 5. Approval tab – HR / Admin / MD (single API by role)

One endpoint; response depends on the logged-in user’s role:

- **HR**: applications where `HR_approval` = Pending.
- **Admin**: applications where `admin_approval` = Pending.
- **MD**: applications where `MD_approval` = Pending.
- Other roles: empty array `[]`.

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/approval/` |

**Headers**

- Session cookie.

**Body**

- None.

**Success response** – `200 OK`

```json
[
  {
    "id": 1,
    "applicant": 1,
    "applicant_username": "john",
    "team_lead": 2,
    "team_lead_username": "jane_lead",
    "start_date": "2026-03-20",
    "duration_of_days": 2,
    "live_subject": "Personal leave",
    "reason": "Family event.",
    "leave_type": 1,
    "leave_type_name": "Full_day",
    "half_day_slots": null,
    "team_lead_approval": 2,
    "team_lead_approval_status": "Pending",
    "HR_approval": 2,
    "hr_approval_status": "Pending",
    "MD_approval": 2,
    "md_approval_status": "Pending",
    "admin_approval": null,
    "admin_approval_status": null,
    "is_emergency": false,
    "application_date": "2026-03-10",
    "approved_by_MD_at": null
  }
]
```

MD sees the same full structure (all fields at MD level).

---

## 6. List all leave applications

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/` |

**Success response** – `200 OK`: array of leave application objects (same structure as above).

---

## 7. Retrieve one leave application

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/<id>/` |

**Example:** `GET {{baseurl}}/accounts/leave-applications/1/`

**Success response** – `200 OK`: single leave application object.

**Error:** `404` if not found.

---

## 8. Update leave application (PATCH)

Used to approve/reject (Team lead, HR, Admin, MD) or to edit draft (applicant). Only allowed fields are applied per role.

| Field    | Value |
|----------|--------|
| **Method** | `PATCH` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/<id>/` |

**Headers**

- `Content-Type: application/json`

**Body** – raw JSON (partial; only send fields you are allowed to change)

**Team lead** – set own approval:

```json
{
  "team_lead_approval": 1
}
```

(1 = Approved, 2 = Pending, 3 = Rejected; use LeaveStatus PKs from your DB.)

**HR** – set HR approval:

```json
{
  "HR_approval": 1
}
```

**Admin** – set admin approval:

```json
{
  "admin_approval": 1
}
```

**MD** – set MD approval (and sets `approved_by_MD_at` when Approved):

```json
{
  "MD_approval": 1
}
```

**Applicant** – edit draft (only if no approval is yet Approved):

```json
{
  "start_date": "2026-03-21",
  "duration_of_days": 3,
  "live_subject": "Updated subject",
  "reason": "Updated reason.",
  "leave_type": 1,
  "half_day_slots": null
}
```

**Success response** – `200 OK`: full leave application object.

**Error examples**

- `403` – Not allowed to change this field or application.
- `400` – `{"non_field_errors": ["Cannot edit application after an approval has been granted."]}` (applicant editing after approval).
- `400` – `{"non_field_errors": ["Insufficient leave balance..."]}` when applicant increases duration.

---

## 9. Update leave application (PUT)

Same URL as PATCH; send full allowed payload. Same role rules and response shape as section 8.

| Field    | Value |
|----------|--------|
| **Method** | `PUT` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/<id>/` |

---

## 10. Delete leave application

Applicant can delete own application only if MD has not approved it.

| Field    | Value |
|----------|--------|
| **Method** | `DELETE` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/<id>/` |

**Success response** – `204 No Content` (no body).

**Error examples**

- `403` – `{"detail": "You may only delete your own leave application."}`
- `403` – `{"detail": "Cannot delete an application that has been approved by MD."}`

---

## Quick reference

| Purpose              | Method | URL |
|----------------------|--------|-----|
| Apply for leave      | POST   | `/accounts/leave-applications/` |
| Emergency leave (HR) | POST   | `/accounts/leave-applications/emergency/` |
| My history           | GET    | `/accounts/leave-applications/view_history/` |
| Team lead approval   | GET    | `/accounts/leave-applications/approval_teamlead/` |
| HR/Admin/MD approval| GET    | `/accounts/leave-applications/approval/` |
| List all             | GET    | `/accounts/leave-applications/` |
| Get one              | GET    | `/accounts/leave-applications/<id>/` |
| Update               | PATCH  | `/accounts/leave-applications/<id>/` |
| Update               | PUT    | `/accounts/leave-applications/<id>/` |
| Delete               | DELETE | `/accounts/leave-applications/<id>/` |

**LeaveStatus IDs** (typical): 1 = Approved, 2 = Pending, 3 = Rejected. Confirm in your DB (e.g. `LeaveStatus.objects.values('id', 'name')`).
