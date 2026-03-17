# Alerts & Announcements API – Testing reference

**Base prefix:** `{{baseurl}}/alertsapi/`  
**Auth:** All endpoints require a logged-in user (session/cookie).  
**Content-Type:** `application/json` for POST/PUT/PATCH bodies.

---

## 1. Alert types (read-only)

### List alert types

**url:** `{{baseurl}}/alertsapi/alert-types/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "id": 1, "type_name": "System" },
  { "id": 2, "type_name": "Security" }
]
```
**notes:** All alert types for dropdowns. No query params.

---

### Retrieve alert type

**url:** `{{baseurl}}/alertsapi/alert-types/<id>/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{ "id": 1, "type_name": "System" }
```
**notes:** 404 if id not found.

---

## 2. Alerts (CRUD)

### List alerts

**url:** `{{baseurl}}/alertsapi/alerts/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "id": 1,
    "alert_title": "Server maintenance scheduled",
    "alert_type": "System",
    "alert_severity": "high",
    "creator_name": "Admin User",
    "details": "Maintenance window 2–4 AM IST.",
    "created_at": "09/03/2026 14:30:00",
    "close_at": null,
    "resolved_by_name": null,
    "closed_by": null,
    "status": "PENDING"
  }
]
```
**notes:** Datetime fields in IST (d/m/y H:M:S). `alert_creator` and `resolved_by` usernames not in response; `creator_name` and `resolved_by_name` are full names.

---

### Retrieve alert

**url:** `{{baseurl}}/alertsapi/alerts/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Same shape as one item in list above.  
**notes:** 404 if id not found.

---

### Create alert

**url:** `{{baseurl}}/alertsapi/alerts/`  
**method:** POST  
**body:**
```json
{
  "alert_title": "Server maintenance scheduled",
  "alert_type": "System",
  "alert_severity": "high",
  "resolved_by": "admin",
  "closed_by": "2026-03-15T10:30:00",
  "details": "Maintenance window 2–4 AM IST.",
  "status": "PENDING"
}
```
**sample_response:**
```json
{
  "id": 1,
  "alert_title": "Server maintenance scheduled",
  "alert_type": "System",
  "alert_severity": "high",
  "creator_name": "Admin User",
  "details": "Maintenance window 2–4 AM IST.",
  "created_at": "09/03/2026 14:30:00",
  "close_at": null,
  "resolved_by_name": null,
  "closed_by": null,
  "status": "PENDING"
}
```
**notes:** `alert_title`, `alert_type`, `alert_severity`, `resolved_by`, `closed_by` required. `alert_type` must match existing alert type name. `alert_severity`: high | medium | low. `closed_by` ISO 8601. `alert_creator` set from logged-in user. 201 on success.

---

### Update alert (PUT / PATCH)

**url:** `{{baseurl}}/alertsapi/alerts/<id>/`  
**method:** PUT or PATCH  
**body:**
```json
{
  "close_at": "2026-03-15T10:30:00",
  "resolved_by": "admin",
  "closed_by": "2026-03-15T10:30:00",
  "status": "COMPLETED"
}
```
**sample_response:** Full alert object (same shape as list/retrieve).  
**notes:** PATCH accepts partial fields. Request datetimes ISO 8601; response datetimes IST d/m/y H:M:S. 404 if id not found.

---

### Delete alert

**url:** `{{baseurl}}/alertsapi/alerts/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if id not found.

---

## 3. Announcement types (read-only)

### List announcement types

**url:** `{{baseurl}}/alertsapi/announcement-types/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  { "id": 1, "type_name": "Product" },
  { "id": 2, "type_name": "General" }
]
```
**notes:** All announcement types. No query params.

---

### Retrieve announcement type

**url:** `{{baseurl}}/alertsapi/announcement-types/<id>/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{ "id": 1, "type_name": "Product" }
```
**notes:** 404 if id not found.

---

## 4. Announcements (CRUD)

### List announcements

**url:** `{{baseurl}}/alertsapi/announcements/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "id": 1,
    "announcement": "New product launch next week.",
    "created_by": "admin",
    "creator_name": "Admin User",
    "type": "Product",
    "product": "Product A",
    "percentage": 15,
    "created_at": "2026-03-09T09:00:00Z",
    "created_at_ist": "09/03/2026 14:30:00"
  }
]
```
**notes:** `type` and `product` are type/product names. `created_at_ist` in IST d/m/y H:M:S.

---

### Retrieve announcement

**url:** `{{baseurl}}/alertsapi/announcements/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Same shape as one item in list above.  
**notes:** 404 if id not found.

---

### Create announcement

**url:** `{{baseurl}}/alertsapi/announcements/`  
**method:** POST  
**body:**
```json
{
  "announcement": "New product launch next week.",
  "type": "Product",
  "product": "Product A",
  "percentage": 15
}
```
**sample_response:** Created announcement object (same shape as list/retrieve).  
**notes:** `announcement` and `type` required. `type` must match announcement type name. `product` optional, must match Product.name. `created_by` set from logged-in user. 201 on success.

---

### Update announcement (PUT / PATCH)

**url:** `{{baseurl}}/alertsapi/announcements/<id>/`  
**method:** PUT or PATCH  
**body:**
```json
{
  "announcement": "Updated announcement text.",
  "percentage": 20
}
```
**sample_response:** Full announcement object (same shape as list/retrieve).  
**notes:** PATCH accepts partial fields. 404 if id not found.

---

### Delete announcement

**url:** `{{baseurl}}/alertsapi/announcements/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if id not found.
