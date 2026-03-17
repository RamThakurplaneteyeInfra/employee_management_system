# Task Management API – Testing reference

**Base prefix:** `{{baseurl}}/tasks/`  
**Auth:** All endpoints require a logged-in user (session/cookie).  
**Content-Type:** `application/json` for POST/PATCH/PUT bodies.

---

## 1. Home

**url:** `{{baseurl}}/tasks/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{ "message": "You are at tasks page" }
```
**notes:** Tasks landing; no query params.

---

## 2. Filters

### getNamesfromRoleandDesignation

**url:** `{{baseurl}}/tasks/getNamesfromRoleandDesignation/`  
**method:** GET  
**body:** None  
**query params:** Optional `role` and/or `designation` (filter by role name and/or designation name).  
**sample_response:**
```json
[
  { "Name": "Alice Smith" },
  { "Name": "Bob Jones" }
]
```
**notes:** Returns Profile names for "Assigned to" dropdown. Excludes current user. If both role and designation omitted, returns all other users. Invalid role/designation returns 404 with message.

---

### getTaskTypes

**url:** `{{baseurl}}/tasks/getTaskTypes/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "type_name": "SOS" },
  { "type_name": "1 Day" },
  { "type_name": "10 Day" },
  { "type_name": "Monthly" },
  { "type_name": "Quaterly" }
]
```
**notes:** All task types for dropdown.

---

### getTaskStatuses

**url:** `{{baseurl}}/tasks/getTaskStatuses/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "status_name": "PENDING" },
  { "status_name": "INPROCESS" },
  { "status_name": "COMPLETED" }
]
```
**notes:** All task statuses for dropdown.

---

## 3. Tasks

### createTask

**url:** `{{baseurl}}/tasks/createTask/`  
**method:** POST  
**body:**
```json
{
  "title": "Review report",
  "description": "Complete Q1 review",
  "due_date": "2026-03-20",
  "type": "1 Day",
  "assigned_to": ["user1", "user2"]
}
```
**sample_response:**
```json
{ "message": "Task created" }
```
**notes:** All of `title`, `description`, `due_date`, `assigned_to`, `type` are required. `type` must match an existing TaskTypes.type_name. 201 on success; 400 if any required field missing; 403/404 on invalid type or user.

---

### changeStatus

**url:** `{{baseurl}}/tasks/changeStatus/<task_id>/`  
**method:** PATCH  
**body:**
```json
{ "change_Status_to": "COMPLETED" }
```
**sample_response:**
```json
{ "message": "Status Changed to COMPLETED" }
```
**notes:** `change_Status_to` must match an existing TaskStatus.status_name (e.g. PENDING, INPROCESS, COMPLETED). 404 if task not found.

---

### updateTask

**url:** `{{baseurl}}/tasks/updateTask/<task_id>/`  
**method:** PATCH  
**body:**
```json
{
  "title": "Updated title",
  "description": "Updated description",
  "due_date": "2026-03-25",
  "type": "Monthly"
}
```
**sample_response:**
```json
{ "message": "Task updated successfully" }
```
**notes:** Only task creator can update. Partial body allowed. 403 if not creator; 404 if task not found.

---

### viewTasks

**url:** `{{baseurl}}/tasks/viewTasks/`  
**method:** GET  
**body:** None  
**query params:** Optional `type` — one of `all`, `SOS`, `1 Day`, `10 Day`, `Monthly`, `Quaterly`.  
**sample_response:**
```json
[
  {
    "Task_id": 1,
    "Title": "Review report",
    "Description": "Complete Q1 review",
    "Status": "PENDING",
    "Created_by": "Admin User",
    "Report_to": "Admin User",
    "Assigned_to": [
      { "name": "Alice Smith", "role": "Developer" },
      { "name": "Bob Jones", "role": null }
    ],
    "Due_date": "20/03/2026",
    "Created_at": "09/03/2026 14:30:00",
    "Task_type": "1 Day",
    "completed_At": null,
    "unseen_count": 2
  }
]
```
**notes:** Returns tasks **created by** the current user. Dates/times in IST. `unseen_count` is task-message unseen count for current user (0 for creator). `completed_At` set when status is COMPLETED (from status change log).

---

### viewAssignedTasks

**url:** `{{baseurl}}/tasks/viewAssignedTasks/`  
**method:** GET  
**body:** None  
**query params:** Optional `type` — same as viewTasks.  
**sample_response:** Same shape as viewTasks list.  
**notes:** Returns tasks **assigned to** the current user (not created by them).

---

### deleteTask

**url:** `{{baseurl}}/tasks/deleteTask/<task_id>/`  
**method:** DELETE  
**body:** None  
**sample_response:**
```json
{ "Message": "task-task_id 1 deleted successfully" }
```
**notes:** Allowed for task creator or users with role MD/TeamLead. 403 if not authorised; 404 if task not found.

---

### Taskcount

**url:** `{{baseurl}}/tasks/Taskcount/<username>/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "status": "PENDING", "count": 5 },
  { "status": "INPROCESS", "count": 2 },
  { "status": "COMPLETED", "count": 10 }
]
```
**notes:** Count of assigned tasks per status for the given username. 400 if user not found.

---

## 4. Task messaging

### sendMessage

**url:** `{{baseurl}}/tasks/sendMessage/`  
**method:** POST  
**body:**
```json
{
  "task_id": 1,
  "message": "Please complete by EOD."
}
```
**sample_response:**
```json
{ "status": "Message sent" }
```
**notes:** `message` and `task_id` required. Sender must be task creator or assignee. Increments unseen_count for other assignees. 201 on success; 400 if message missing; 500 on task/user errors.

---

### getMessage

**url:** `{{baseurl}}/tasks/getMessage/<task_id>/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "sender": "admin",
    "full_name": "Admin User",
    "message": "Please complete by EOD.",
    "date": "09/03/2026",
    "time": "14:30:00"
  }
]
```
**notes:** Only task creator or assignees. Marks messages as seen for current user (resets unseen_count). Messages ordered by created_at descending. 403 if not authorised.

---

### markTaskMessagesSeen

**url:** `{{baseurl}}/tasks/markTaskMessagesSeen/<task_id>/`  
**method:** POST  
**body:** None (or empty JSON)  
**sample_response:**
```json
{ "status": "ok", "unseen_count": 0 }
```
**notes:** Resets unseen_count to 0 for current user for this task. Caller must be creator or assignee. 403 if not authorised; 404 if task not found.
