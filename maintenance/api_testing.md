# Maintenance APIs / Commands – Testing reference

This app mostly contains **management commands** (e.g., `populate_leave_data`, `addEntries`) rather than HTTP APIs.

Use this file to document:

- How to run each management command.
- Any admin-only HTTP endpoints (if later added under `maintenance/urls.py`).

---

## 1. Management commands

Examples:

- `python manage.py populate_leave_data`
- `python manage.py addEntries`

> For each command, add:
> - Purpose
> - Arguments / options
> - Expected side effects on the database.

