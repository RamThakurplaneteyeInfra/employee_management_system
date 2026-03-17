# Project API – Testing reference

**Base prefix:** `{{baseurl}}/projectapi/`  
**Auth:** All endpoints require a logged-in user.  
**Content-Type:** `application/json` for POST body.

---

## 1. Products – List

**url:** `{{baseurl}}/projectapi/products/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "id": 1, "name": "Product A", "description": "Description for A" },
  { "id": 2, "name": "Product B", "description": "" }
]
```
**notes:** All products ordered by name. Used by QuaterlyReports and Clients.

---

## 2. Products – Create

**url:** `{{baseurl}}/projectapi/products/create/`  
**method:** POST  
**body:**
```json
{ "name": "Product C", "description": "Optional description" }
```
**sample_response:**
```json
{ "id": 3, "name": "Product C", "description": "Optional description" }
```
**notes:** `name` required; `description` optional. 201 on success. 400 if name missing; 409 if a product with this name already exists.
