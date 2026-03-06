# Accounts APIs – Testing reference

> This file documents all executable APIs under the `accounts/` namespace, including core accounts endpoints and leave management.

---

## Core Accounts APIs

(Moved from project-level `api_testing.md`.)

<!-- BEGIN: original api_testing.md content -->
1. ## Login

##### URL-{{base URL}}/accounts/login/

response-{

    "message": "You are logged in",

    "username": "0001",

    "Role": "Admin"

}



## 2\. Get Employee

##### URL-{{base BASE}}/accounts/employee/dashboard/

response-[

    {

        "Employee\_id": "0001",

        "Email\_id": "admin@planetfarm.ai",

        "Date\_of\_birth": "2020-02-02",

        "Date\_of\_join": "2020-02-04",

        "Name": "Jadhav",

        "Photo\_link": "",

        "role": "Admin"

    }

]



## 3.AllEmployees

##### URL-{{base URL}}/accounts/employees/

response-[

    {

        "Employee\_id": "2000",

        "Name": "Tushar Patil",

        "Role": "MD",

        "Branch": null,

        "Designation": null,

        "Date\_of\_birth": "1995-01-01",

        "Date\_of\_join": "2026-01-20",

        "Number\_of\_days\_from\_joining": "0 years 3 days",

        "Email\_id": "Tushar@gmail.com",

        "Photo\_link": "/media/profile\_images/Screenshot\_2025-10-29\_154813.png",

        "teamlead": null,

        "function": null

    },

    {

        "Employee\_id": "20011",

        "Name": "tejraj D",

        "Role": "TeamLead",

        "Branch": "Farm Core",

        "Designation": "Precision Agriculture Manager",

        "Date\_of\_birth": "1999-02-02",

        "Date\_of\_join": "2025-01-01",

        "Number\_of\_days\_from\_joining": "1 years 22 days",

        "Email\_id": "Tejarj@gmail.com",

        "Photo\_link": "/media/profile\_images/Tejraj\_Dhongade.jfif",

        "department": "Sales",

        "Teamleader": null,

        "function": "IP"

    },

    {

        "Employee\_id": "3000",

        "Name": "Snighdha",

        "Role": "TeamLead",

        "Branch": "Technology",

        "Designation": "Software Developer",

        "Date\_of\_birth": "2020-02-02",

        "Date\_of\_join": "2020-12-01",

        "Number\_of\_days\_from\_joining": "5 years 53 days",

        "Email\_id": "dummy@nashik.com",

        "Photo\_link": "/media/profile\_images/vendor.jpg",

        "department": "Production",

        "Teamleader": null,

        "function": "IP"

    },

    {

        "Employee\_id": "3001",

        "Name": "siddhi borse",

        "Role": "Employee",

        "Branch": "Farm Core",

        "Designation": "Digital Marketing Manager",

        "Date\_of\_birth": "2001-01-02",

        "Date\_of\_join": "2025-01-02",

        "Number\_of\_days\_from\_joining": "1 years 21 days",

        "Email\_id": "siddhi@gmail.com",

        "Photo\_link": "/media/profile\_images/Siddhi\_Borase.jfif",

        "department": "Sales",

        "Teamleader": null,

        "function": "IP"

    },

    {

        "Employee\_id": "9000",

        "Name": "Himalaya",

        "Role": "Intern",

        "Branch": "Farm Tech",

        "Designation": "Software Developer",

        "Date\_of\_birth": "2020-02-02",

        "Date\_of\_join": "2020-12-12",

        "Number\_of\_days\_from\_joining": "5 years 42 days",

        "Email\_id": "dummy@gmail.com",

        "Photo\_link": "/media/profile\_images/IMG\_0395.jpg",

        "department": "Business Strategy",

        "Teamleader": "Snighdha",

        "function": "HC"

    },

    {

        "Employee\_id": "00110011",

        "Name": "abcdefg",

        "Role": "MD",

        "Branch": null,

        "Designation": null,

        "Date\_of\_birth": "2002-11-10",

        "Date\_of\_join": "2002-11-10",

        "Number\_of\_days\_from\_joining": "23 years 74 days",

        "Email\_id": "user@planeteye",

        "Photo\_link": "/media/profile\_images/Screenshot\_2025-05-29\_182812.png",

        "teamlead": null,

        "function": null

    }

]



## 4.ChangePassword

##### URL-{{base URL}}/accounts/admin/changePassword/[slug:u](slug:u)/

path parameter- username(u)

body-{"new\_password":"123"}

response-

{"message": "Password is changed to 123"}



## 5.CreateLogin

##### URL-{{base URL}}/accounts/admin/createEmployeeLogin/

response-

{

    "message": "user profile created successfully"

}



## 6.GetBranches

##### URL-{{base URL}}/accounts/getBranch/?Role=

response-

[

    {

        "branch\_name": "Farm Core"

    },

    {

        "branch\_name": "Farm Tech"

    },

    {

        "branch\_name": "Infra Core"

    },

    {

        "branch\_name": "Infra Tech"

    },

    {

        "branch\_name": "Technology"

    }

]



## 7.GetDepartments\&Functions

##### URL-{{base URL}}/accounts/getDepartmentsandFunctions/?Role=

response-



{

    "Departments": [

        "Accounts\&Finance",

        "Business Strategy",

        "HR",

        "Legal\&Document",

        "Marketing",

        "NPC",

        "NPD",

        "Production",

        "Purchase",

        "R\&D",

        "Sales",

        "Vigil"

    ],

    "functions": [

        "NPD",

        "MMR",

        "RG",

        "HC",

        "IP"

    ]

}



## 8.GetRoles

##### URL-{{base URL}}/accounts/getRoles/

response-

[

    {

        "role\_name": "MD"

    },

    {

        "role\_name": "Intern"

    },

    {

        "role\_name": "TeamLead"

    },

    {

        "role\_name": "Employee"

    }

]



## 9.GetDesignations

##### URL-{{base URL}}/accounts/getDesignations/?Role=

response-

[

    {

        "designation": "Software Developer"

    },

    {

        "designation": "Python Developer"

    },

    {

        "designation": "AI/ML Developer"

    },

    {

        "designation": "Web Developer"

    },

    {

        "designation": "Backend Developer"

    },

    {

        "designation": "Precision Agriculture Manager"

    },

    {

        "designation": "Digital Marketing Manager"

    },

    {

        "designation": "Project Supervisor"

    },

    {

        "designation": "Designer Engineer"

    },

    {

        "designation": "Site Engineer"

    },

    {

        "designation": "Field Officer"

    }

]



## 10.GetTeamleads

##### URL-{{base URL}}/accounts/getTeamleads/?Role

response-

[

    {

        "Name": "Snighdha",

        "Employee\_id": "3000"

    },

    {

        "Name": "tejraj D",

        "Employee\_id": "20011"

    }

]



## 11.DeleteUser

##### URL-{{base URL}}/accounts/admin/deleteEmployee/[slug:u](slug:u)/

path parameter-username(u)

response-

{"message": "user deleted successfully"}



## 12.UpdateUser

##### URL-{{base URL}}/accounts/admin/updateProfile/[slug:username](slug:username)/

path parameter- username

response-





## 13.Logout

##### URL-{{base URL}}/accounts/logout/

response-

{

    "message": "Logout successfully 0001"

}
<!-- END: original api_testing.md content -->

---

## Leave Management APIs

(Moved from project-level `leave_api_testing.md`.)

<!-- BEGIN: leave_api_testing.md content -->
# Leave APIs – Testing reference

Base URL: `http://localhost:8000` (or your server).  
All endpoints under `/accounts/leave-applications/` require **logged-in user** (session/cookie auth).  
Use the same session as for other accounts APIs (e.g. after `POST /accounts/login/`).

**Input rule (every leave API):** Request bodies use **character/string** for all FK-like fields (never PKs).  
- **Approval fields (PATCH/PUT):** `"Approved"`, `"Pending"`, `"Rejected"`.  
- **leave_type (POST create, POST emergency, PATCH/PUT draft):** `"Full_day"` or `"Half_day"`.  
- **applicant (POST emergency only):** username string.

**Response rule:** Every leave API response returns **strings** for FK-backed data (no FK ids).  
- `applicant_name`, `team_lead_name` from Profile; `leave_type_name`; `team_lead_approval_status`, `hr_approval_status`, `md_approval_status`, `admin_approval_status`.

---


## 1. Create leave application (self)

Apply for leave as the logged-in user. Remaining-leaves balance is validated. Approval chain is set by role (TeamLead → HR → MD, or Admin → HR → MD, etc.). `team_lead` is auto-filled from Profile. **Input:** `leave_type` as string (`"Full_day"` / `"Half_day"`). **Response:** strings only (no FK ids).

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
  "leave_subject": "Personal leave",
  "reason": "Family event.",
  "leave_type": "Full_day",
  "half_day_slots": null,
  "is_emergency": false
}
```

| Key               | Type    | Required | Description |
|-------------------|---------|----------|-------------|
| start_date        | string  | Yes      | Date (YYYY-MM-DD). |
| duration_of_days  | integer | Conditional | For **Full_day**: required, ≥ 1. For **Half_day**: optional (defaults to 1). |
| leave_subject      | string  | Yes      | Short subject. |
| reason            | string  | Yes      | Leave reason. |
| leave_type        | string  | Yes      | `"Full_day"` or `"Half_day"`. |
| half_day_slots    | string  | Conditional | For **Half_day**: required, `"First_Half"` or `"Second_Half"`. For Full_day: omit or null. |
| is_emergency      | boolean | No       | Default `false`. |

**Success response** – `201 Created` (no FK ids; user names from Profile)

```json
{
  "id": 1,
  "applicant_name": "John Doe",
  "team_lead_name": "Jane Smith",
  "start_date": "2026-03-20",
  "duration_of_days": 2,
  "leave_subject": "Personal leave",
  "reason": "Family event.",
  "leave_type_name": "Full_day",
  "half_day_slots": null,
  "team_lead_approval_status": "Pending",
  "hr_approval_status": "Pending",
  "md_approval_status": "Pending",
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

HR creates leave on behalf of any user. Emergency leaves are limited to **10% of the user's total_leaves** (tracked in `LeaveSummary.emergency_leaves` as used emergency days). Each emergency day also counts as **used_leaves** and reduces `remaining_leaves`. For emergency requests, team lead, HR, and MD approvals are all set to **Approved** by default (they can still be updated later via PATCH/PUT).

| Field    | Value |
|----------|--------|
| **Method** | `POST` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/emergency/` |

**Headers**

- `Content-Type: application/json`

**Body** – raw JSON

```json
{
  "applicant": "john_doe",
  "start_date": "2026-03-22",
  "duration_of_days": 1,
  "leave_subject": "Emergency",
  "reason": "Medical.",
  "leave_type": "Full_day",
  "half_day_slots": null,
  "note": "Severe medical emergency."
}
```

| Key               | Type   | Required | Description |
|-------------------|--------|----------|-------------|
| applicant         | string | Yes      | **Username** (auth_user) of the employee on whose behalf leave is created. |
| start_date        | string | Yes      | YYYY-MM-DD. |
| duration_of_days  | int    | Yes      | ≥ 1. |
| leave_subject     | string | Yes      | Subject. |
| reason            | string | Yes      | Reason. |
| leave_type        | string | Yes      | `"Full_day"` or `"Half_day"` (character, not PK). |
| half_day_slots    | string | No       | `"First_Half"` / `"Second_Half"` or null. |
| note              | string | No       | Optional note from HR describing the emergency leave. |

**Success response** – `201 Created` (same shape as in section 1: no FK ids, `applicant_name` / `team_lead_name` from Profile, with `is_emergency: true`; approvals default to `"Approved"`).

**Error examples**

- `403` – User is not HR.
- `400` – Validation errors.

---

## 3. My leave summary (balance)

Logged-in user’s leave balance from the LeaveSummary table: `total_leaves`, `used_leaves`, `remaining_leaves`, and emergency usage.

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/summary/` |

**Headers**

- Session cookie.

**Body**

- None.

**Success response** – `200 OK`

```json
{
  "total_leaves": 20,
  "used_leaves": 3,
  "remaining_leaves": 17,
  "emergency_leaves": 1
}
```

If the user has no LeaveSummary row, one is created with `total_leaves: 0`, `used_leaves: 0`, `remaining_leaves: 0`, `emergency_leaves: 0`.

---

## 4. View history (my applications)

Logged-in user’s own leave applications.

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/view_history/` |

**Headers**

- None beyond session cookie.

**Body**

- None.

**Success response** – `200 OK` (no FK ids; user names from Profile)

```json
[
  {
    "id": 1,
    "applicant_name": "John Doe",
    "team_lead_name": "Jane Smith",
    "start_date": "2026-03-20",
    "duration_of_days": 2,
    "leave_subject": "Personal leave",
    "reason": "Family event.",
    "leave_type_name": "Full_day",
    "half_day_slots": null,
    "team_lead_approval_status": "Pending",
    "hr_approval_status": "Pending",
    "md_approval_status": "Pending",
    "admin_approval_status": null,
    "is_emergency": false,
    "application_date": "2026-03-10",
    "approved_by_MD_at": null
  }
]
```

---

## 5. Approval tab (Team lead + HR / Admin / MD – single API)

Single endpoint for all approval tasks. Returns leave applications by role and hierarchy:

- **Team lead**: **all** leave applications where `team_lead` = current user (irrespective of approval status).
- **HR**: **all** applications that have been **approved by team lead** (`team_lead_approval` = Approved), regardless of HR’s own status (history + pending).
- **Admin**: **all** applications that have been **approved by team lead** (`team_lead_approval` = Approved), regardless of admin’s own status.
- **MD**: **all** applications that have been **approved by HR or Admin** (`HR_approval` = Approved or `admin_approval` = Approved), regardless of MD’s own status.

If the user has multiple roles (e.g. team lead and HR), the list is the union of the above (no duplicate rows).

| Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/approval/` 

**Headers**

- Session cookie.

**Body**

- None.

**Success response** – `200 OK` (no FK ids; user names from Profile)

```json
[
  {
    "id": 1,
    "applicant_name": "John Doe",
    "team_lead_name": "Jane Smith",
    "start_date": "2026-03-20",
    "duration_of_days": 2,
    "leave_subject": "Personal leave",
    "reason": "Family event.",
    "leave_type_name": "Full_day",
    "half_day_slots": null,
    "team_lead_approval_status": "Pending",
    "hr_approval_status": "Pending",
    "md_approval_status": "Pending",
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

<!-- | Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/` |

**Success response** – `200 OK`: array of leave application objects (same structure as above: no FK ids, `applicant_name` / `team_lead_name` from Profile). -->

---

## 7. Retrieve one leave application

<!-- | Field    | Value |
|----------|--------|
| **Method** | `GET` |
| **URL**    | `{{baseurl}}/accounts/leave-applications/<id>/` |

**Example:** `GET {{baseurl}}/accounts/leave-applications/1/`

**Success response** – `200 OK`: single leave application object (same format: no FK ids, `applicant_name` / `team_lead_name` from Profile).

**Error:** `404` if not found. -->

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

**Team lead** – set own approval (use status **name**, not PK):

```json
{
  "team_lead_approval": "Rejected"
}
```

(Allowed values: `"Approved"`, `"Pending"`, `"Rejected"`.)

**HR** – set HR approval:

```json
{
  "HR_approval": "Approved"
}
```

**Admin** – set admin approval:

```json
{
  "admin_approval": "Pending"
}
```

**MD** – set MD approval (and sets `approved_by_MD_at` when Approved):

```json
{
  "MD_approval": "Approved"
}
```

**Applicant** – edit draft (only if no approval is yet Approved). Use **string** for `leave_type` (not PK):

```json
{
  "start_date": "2026-03-21",
  "duration_of_days": 3,
  "leave_subject": "Updated subject",
  "reason": "Updated reason.",
  "leave_type": "Full_day",
  "half_day_slots": null
}
```

**Success response** – `200 OK`: full leave application object (same format: no FK ids, `applicant_name` / `team_lead_name` from Profile).

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
| My leave summary     | GET    | `/accounts/leave-applications/summary/` |
| My history           | GET    | `/accounts/leave-applications/view_history/` |
| Approval (team lead / HR / Admin / MD) | GET | `/accounts/leave-applications/approval/` |
| List all             | GET    | `/accounts/leave-applications/` |
| Get one              | GET    | `/accounts/leave-applications/<id>/` |
| Update               | PATCH  | `/accounts/leave-applications/<id>/` |
| Update               | PUT    | `/accounts/leave-applications/<id>/` |
| Delete               | DELETE | `/accounts/leave-applications/<id>/` |

**Input rule (all leave APIs):** Send **strings** for any FK-like field (no PKs).  
- **Approval (PATCH/PUT):** `"Approved"`, `"Pending"`, `"Rejected"`.  
- **leave_type (POST create, POST emergency, PATCH/PUT draft):** `"Full_day"` or `"Half_day"`.  
- **applicant (POST emergency):** username string.  

**Response rule:** All leave responses return **strings** for FKs (e.g. `applicant_name`, `team_lead_name`, `leave_type_name`, `*_approval_status`); no FK ids in the body.
<!-- END: leave_api_testing.md content -->

