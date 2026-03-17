# Notifications API – Testing reference

**Base prefix:** `{{baseurl}}/notifications/`  
**Auth:** List and mark-as-read require a logged-in user; types and cron are permissionless (cron requires X-CRON-KEY).  
**Content-Type:** `application/json` where applicable.

---

## 1. Today's notifications (list)

**url:** `{{baseurl}}/notifications/today/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "id": 1,
    "notification_type": "Task Assigned",
    "from_user": "Admin User",
    "receipient": "John Doe",
    "message": "You have been assigned a new task.",
    "is_read": false,
    "created_at": "09/03/26 14:30:00"
  }
]
```
**notes:** Notifications for logged-in user (receipient), ordered by created_at descending. created_at in IST. from_user/receipient are display names.

---

## 2. Notification types

**url:** `{{baseurl}}/notifications/types/`  
**method:** GET  
**body:** None  
**sample_response:** Array of notification type objects (from notification_type model; typically id, type_name, etc.).  
**notes:** AllowAny. 500 with error message on exception.

---

## 3. Mark as read

**url:** `{{baseurl}}/notifications/read/<pk>/`  
**method:** POST  
**body:** None (or empty JSON)  
**sample_response:**
```json
{ "status": "read" }
```
**notes:** Sets is_read=True for the notification. Authenticated. 404 if pk not found (or 500 if get() raises).

---

## 4. Cron – delete seen older than 1 day

**url:** `{{baseurl}}/notifications/cron/delete-seen-older-than-day/`  
**method:** GET  
**body:** None  
**headers:** `X-CRON-KEY`: must match settings.X_CRON_KEY.  
**sample_response:**
```json
{ "deleted": 42 }
```
**notes:** Deletes notifications where is_read=True and created_at date is not today. 403 if X-CRON-KEY missing or wrong.

---

## 5. Cron – delete unseen older than 1 week

**url:** `{{baseurl}}/notifications/cron/delete-unseen-older-than-week/`  
**method:** GET  
**body:** None  
**headers:** `X-CRON-KEY`: must match settings.X_CRON_KEY.  
**sample_response:**
```json
{ "deleted": 10 }
```
**notes:** Deletes notifications where is_read=False and created_at older than 7 days. 403 if X-CRON-KEY missing or wrong.
