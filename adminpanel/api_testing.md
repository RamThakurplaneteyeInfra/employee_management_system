# Admin Panel APIs – Testing reference

Base prefix: `{{baseurl}}/adminapi/`

Use this file to document all executable APIs in the `adminpanel` app (dashboard, admin-only resources).

---

## 1. DRF router endpoints

`adminpanel/urls.py` includes a DRF router:

- `GET {{baseurl}}/adminapi/` – list registered admin viewsets.
- `...` – additional endpoints per registered viewset (see `adminpanel/views.py`).

> For each viewset, add:
> - Base URL
> - Methods supported (list, retrieve, create, update, delete)
> - Example requests and responses.

---

## 2. Dashboard summary

- `GET {{baseurl}}/adminapi/dashboard/` – returns summary metrics for the EMS dashboard.

> Add detailed response structure and any query params here.

