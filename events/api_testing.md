# Events API – Testing reference

**Base prefix:** `{{baseurl}}/eventsapi/`  
**Auth:** Most endpoints require a logged-in user (session/cookie); exceptions noted.  
**Content-Type:** `application/json` for POST/PUT/PATCH bodies.

---

## 1. BookSlots

### List bookslots

**url:** `{{baseurl}}/eventsapi/bookslots/`  
**method:** GET  
**body:** None  
**query params:** Optional `month`, `year` (filter by created_at month/year; default current month/year).  
**sample_response:**
```json
[
  {
    "id": 1,
    "meeting_title": "Sprint planning",
    "date": "2026-03-15",
    "start_time": "10:00:00",
    "end_time": "11:00:00",
    "room": "Conference Room 1",
    "description": "",
    "meeting_type": "group",
    "status": "Confirmed",
    "members": ["user1", "user2"],
    "created_at": "09/03/2026 14:30:00",
    "member_details": [{"full_name": "Alice"}, {"full_name": "Bob"}],
    "creater_details": {"full_name": "Admin"}
  }
]
```
**notes:** Authenticated. Dates/times in serializer format; created_at in IST.

---

### Retrieve bookslot

**url:** `{{baseurl}}/eventsapi/bookslots/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Same shape as one item in list.  
**notes:** 404 if id not found.

---

### Create bookslot

**url:** `{{baseurl}}/eventsapi/bookslots/`  
**method:** POST  
**body:**
```json
{
  "meeting_title": "Sprint planning",
  "date": "2026-03-15",
  "start_time": "10:00:00",
  "end_time": "11:00:00",
  "room": "Conference Room 1",
  "description": "",
  "meeting_type": "group",
  "status": "Confirmed",
  "members": ["user1", "user2"]
}
```
**sample_response:** Created slot object (same shape as list).  
**notes:** `created_by` set from logged-in user. Validation: end_time > start_time, at least one member, no double-booking of same room in same time range, creator not in overlapping slot. 201 on success.

---

### Update bookslot (PUT / PATCH)

**url:** `{{baseurl}}/eventsapi/bookslots/<id>/`  
**method:** PUT or PATCH  
**body:** Same fields as create (partial allowed for PATCH).  
**example body (mark Done + optional done-fields):**
```json
{
  "status": "Done",
  "notes": null,
  "need_more_discussion": "More time needed for this point.",
  "dispute": "",
  "in_future": "Will revisit next month.",
  "deliverable": "Final report draft.",
  "not_deliverable": null,
  "opportunity": "Good chance for follow-up project."
}
```
**sample_response:** Updated slot object.  
**notes:** 404 if id not found.

---

### Delete bookslot

**url:** `{{baseurl}}/eventsapi/bookslots/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if id not found.

---

### Bookslots today

**url:** `{{baseurl}}/eventsapi/bookslots/today/`  
**method:** GET  
**body:** None  
**sample_response:** Array of bookslot objects (same shape as list) for slots with date = today.  
**notes:** No query params; uses server date.

---

## 2. Tours

### List tours

**url:** `{{baseurl}}/eventsapi/tours/`  
**method:** GET  
**body:** None  
**sample_response:** Array of tour objects (id, name, starting_date, ending_date, location, description, created_by, tour member details, etc.).  
**notes:** Authenticated. Order: -starting_date, -created_at.

---

### Retrieve tour

**url:** `{{baseurl}}/eventsapi/tours/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single tour object.  
**notes:** 404 if id not found.

---

### Create tour

**url:** `{{baseurl}}/eventsapi/tours/`  
**method:** POST  
**body:** Tour fields per TourSerializer (name, starting_date, ending_date, location, members, etc.).  
**sample_response:** Created tour object.  
**notes:** 201 on success.

---

### Update tour (PUT / PATCH)

**url:** `{{baseurl}}/eventsapi/tours/<id>/`  
**method:** PUT or PATCH  
**body:** Tour fields (partial allowed for PATCH).  
**sample_response:** Updated tour object.  
**notes:** 404 if id not found.

---

### Delete tour

**url:** `{{baseurl}}/eventsapi/tours/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if id not found.

---

## 3. Holidays

### List holidays

**url:** `{{baseurl}}/eventsapi/holidays/`  
**method:** GET  
**body:** None  
**sample_response:** Array of holiday objects (id, date, name, holiday_type, etc.).  
**notes:** Authenticated. Create/update/delete restricted to Admin, MD, or HR.

---

### Retrieve holiday

**url:** `{{baseurl}}/eventsapi/holidays/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single holiday object.  
**notes:** 404 if id not found.

---

### Create holiday

**url:** `{{baseurl}}/eventsapi/holidays/`  
**method:** POST  
**body:** Holiday fields per HolidaySerializer.  
**sample_response:** Created holiday object.  
**notes:** Admin/MD/HR only. 201 on success.

---

### Update holiday (PUT / PATCH)

**url:** `{{baseurl}}/eventsapi/holidays/<id>/`  
**method:** PUT or PATCH  
**body:** Holiday fields (partial allowed for PATCH).  
**sample_response:** Updated holiday object.  
**notes:** Admin/MD/HR only. 404 if id not found.

---

### Delete holiday

**url:** `{{baseurl}}/eventsapi/holidays/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** Admin/MD/HR only. 404 if id not found.

---

## 4. Events

### List events

**url:** `{{baseurl}}/eventsapi/events/`  
**method:** GET  
**body:** None  
**sample_response:** Array of event objects per EventSerializer.  
**notes:** Authenticated. Create/update/delete restricted to Admin, MD, or HR.

---

### Retrieve event

**url:** `{{baseurl}}/eventsapi/events/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single event object.  
**notes:** 404 if id not found.

---

### Create event

**url:** `{{baseurl}}/eventsapi/events/`  
**method:** POST  
**body:** Event fields per EventSerializer.  
**sample_response:** Created event object.  
**notes:** Admin/MD/HR only. 201 on success.

---

### Update event (PUT / PATCH)

**url:** `{{baseurl}}/eventsapi/events/<id>/`  
**method:** PUT or PATCH  
**body:** Event fields (partial allowed for PATCH).  
**sample_response:** Updated event object.  
**notes:** Admin/MD/HR only. 404 if id not found.

---

### Delete event

**url:** `{{baseurl}}/eventsapi/events/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** Admin/MD/HR only. 404 if id not found.

---

## 5. Birthday counter

### Bulk increment (POST)

**url:** `{{baseurl}}/eventsapi/events/birthdaycounter/`  
**method:** POST  
**body:**
```json
{ "users": ["username1", "username2"] }
```
**sample_response:**
```json
{
  "updated": [
    { "username": "username1", "birthday_counter": 3 },
    { "username": "username2", "birthday_counter": 1 }
  ],
  "invalidated_cache": true
}
```
**notes:** Increments Profile.birthday_counter for each valid username. Invalid/missing users skipped. 400 if body missing `users` or no valid users. Not under router so path is `events/birthdaycounter/`.

---

### Get counter (GET)

**url:** `{{baseurl}}/eventsapi/events/birthdaycounter/<username>/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{ "birthday_counter": 3 }
```
**notes:** 400 with "user not found" if username or profile not found. Must be GET; use POST .../birthdaycounter/ to update.

---

## 6. Reminders

### List reminders

**url:** `{{baseurl}}/eventsapi/reminders/`  
**method:** GET  
**body:** None  
**query params:** Optional `month` (1–12); default current month in current year.  
**sample_response:**
```json
[
  {
    "id": 1,
    "title": "Call client",
    "date": "2026-03-20",
    "time": "15:30:00",
    "note": "Discuss trial.",
    "created_by": "Full Name",
    "created_at": "20/03/2026 15:30:00"
  }
]
```
**notes:** created_at in IST. created_by is full name.

---

### Retrieve reminder

**url:** `{{baseurl}}/eventsapi/reminders/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Same shape as one item in list.  
**notes:** 404 if id not found.

---

### Create reminder

**url:** `{{baseurl}}/eventsapi/reminders/`  
**method:** POST  
**body:**
```json
{
  "title": "Call client",
  "date": "2026-03-20",
  "time": "15:30:00",
  "note": "Discuss trial."
}
```
**sample_response:** Created reminder (same shape as list).  
**notes:** title and date required; time and note optional. created_by set from logged-in user. 201 on success.

---

### Update reminder (PUT / PATCH)

**url:** `{{baseurl}}/eventsapi/reminders/<id>/`  
**method:** PUT or PATCH  
**body:** PUT: full fields (title, date, time, note). PATCH: partial.  
**sample_response:** Updated reminder object.  
**notes:** 404 if id not found.

---

### Delete reminder

**url:** `{{baseurl}}/eventsapi/reminders/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if id not found.

---

### Reminders today

**url:** `{{baseurl}}/eventsapi/reminders/today/`  
**method:** GET  
**body:** None  
**sample_response:** Array of reminder objects for date = today (same shape as list).  
**notes:** Ignores month filter; uses server date.

---

## 7. Rooms

### List rooms

**url:** `{{baseurl}}/eventsapi/rooms/`  
**method:** GET  
**body:** None  
**sample_response:** Array of room objects (id, name, etc. per RoomSerializer).  
**notes:** AllowAny.

---

### Retrieve room

**url:** `{{baseurl}}/eventsapi/rooms/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single room object.  
**notes:** 404 if id not found.

---

### Create room

**url:** `{{baseurl}}/eventsapi/rooms/`  
**method:** POST  
**body:** Room fields per RoomSerializer.  
**sample_response:** Created room object.  
**notes:** 201 on success.

---

### Update room (PUT / PATCH)

**url:** `{{baseurl}}/eventsapi/rooms/<id>/`  
**method:** PUT or PATCH  
**body:** Room fields (partial allowed for PATCH).  
**sample_response:** Updated room object.  
**notes:** 404 if id not found.

---

### Delete room

**url:** `{{baseurl}}/eventsapi/rooms/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if id not found.

---

## 8. Booking status

**url:** `{{baseurl}}/eventsapi/status/`  
**method:** GET  
**body:** None  
**sample_response:** Array of status objects (id, status_name, etc. per BookingStatusSerializer).  
**notes:** List booking statuses for dropdowns.

---

**url:** `{{baseurl}}/eventsapi/status/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single status object.  
**notes:** 404 if id not found.

---

Create/update/delete for status follow standard DRF viewset pattern (POST, PUT/PATCH, DELETE) with same base URL and `<id>/` for detail.

---

## 9. Meeting push

### List meetings

**url:** `{{baseurl}}/eventsapi/meetingpush/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
[
  {
    "id": 1,
    "product_name": "Product A",
    "room_name": "Conference Room 1",
    "meeting_type": "group",
    "time": 30,
    "is_active": true,
    "created_at": "09/03/2026 14:30:00"
  }
]
```
**notes:** Response uses names only (no product_id/meeting_room_id). created_at IST. Create/update/delete restricted to Admin, MD, or HR.

---

### Retrieve meeting

**url:** `{{baseurl}}/eventsapi/meetingpush/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Same shape as one item in list.  
**notes:** 404 if id not found.

---

### Create meeting

**url:** `{{baseurl}}/eventsapi/meetingpush/`  
**method:** POST  
**body:**
```json
{
  "product": "Product A",
  "meeting_room": "Conference Room 1",
  "meeting_type": "group",
  "time": 30,
  "is_active": true
}
```
**sample_response:** Created meeting (GET shape: product_name, room_name).  
**notes:** product and meeting_room are **names** (not ids). meeting_type: individual | group. time = duration in minutes. Admin/MD/HR only. WebSocket may broadcast on product channel when product set (category Meeting_push; action Created/updated/reschedule/abandoned). 201 on success.

---

### Update meeting (PUT / PATCH)

**url:** `{{baseurl}}/eventsapi/meetingpush/<id>/`  
**method:** PUT or PATCH  
**body:** Same fields as create (names).  
**sample_response:** Updated meeting object.  
**notes:** Admin/MD/HR only. WebSocket broadcast on time change (reschedule) or other changes (updated); no broadcast on is_active-only change. 404 if id not found.

---

### Delete meeting

**url:** `{{baseurl}}/eventsapi/meetingpush/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** WebSocket may send abandoned. 404 if id not found.

---

### Cron – delete previous days

**url:** `{{baseurl}}/eventsapi/meetingpush/cron/delete-previous-days/`  
**method:** GET  
**body:** None  
**headers:** `X-CRON-KEY`: must match settings.X_CRON_KEY.  
**sample_response:**
```json
{ "deleted": 5 }
```
**notes:** Deletes meetings with created_at date before today. Permissionless except for cron key; 403 if key missing or wrong.
