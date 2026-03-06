# Task Management APIs – Testing reference

Base prefix: `{{baseurl}}/tasks/`

Use this file to document all executable APIs in the `task_management` app (task CRUD, filters, messaging, counts).

---

## 1. Filters

From `task_management/urls.py`:

- `GET {{baseurl}}/tasks/getNamesfromRoleandDesignation/`
- `GET {{baseurl}}/tasks/getTaskTypes/`
- `GET {{baseurl}}/tasks/getTaskStatuses/`

> Add query params and sample responses.

---

## 2. Tasks

- `GET    {{baseurl}}/tasks/` – home
- `POST   {{baseurl}}/tasks/createTask/`
- `PATCH  {{baseurl}}/tasks/changeStatus/<task_id>/`
- `PUT    {{baseurl}}/tasks/updateTask/<task_id>/`
- `GET    {{baseurl}}/tasks/viewTasks/`
- `GET    {{baseurl}}/tasks/viewAssignedTasks/`
- `DELETE {{baseurl}}/tasks/deleteTask/<task_id>/`
- `GET    {{baseurl}}/tasks/Taskcount/<username>/`

> Document payloads and typical responses for each.

---

## 3. Task messaging

- `POST {{baseurl}}/tasks/sendMessage/`
- `GET  {{baseurl}}/tasks/getMessage/<task_id>/`

> Describe how task messages are structured and any pagination rules.

