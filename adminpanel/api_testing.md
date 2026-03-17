# Admin Panel API – Testing reference

**Base prefix:** `{{baseurl}}/adminapi/`  
**Auth:** All endpoints require a logged-in user; ViewSets and dashboard use AdminPermission (admin-only).  
**Content-Type:** `application/json` for request/response where applicable.

---

## 1. Asset types (CRUD)

**url:** `{{baseurl}}/adminapi/asset-types/`  
**method:** GET  
**body:** None  
**sample_response:** Array of asset type objects (id, name, etc. per AssetTypeSerializer).  
**notes:** List. AdminPermission.

---

**url:** `{{baseurl}}/adminapi/asset-types/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single asset type.  
**notes:** Retrieve. 404 if not found.

---

**url:** `{{baseurl}}/adminapi/asset-types/`  
**method:** POST  
**body:** Asset type fields per serializer.  
**sample_response:** Created asset type. 201.  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/asset-types/<id>/`  
**method:** PUT or PATCH  
**body:** Asset type fields (partial for PATCH).  
**sample_response:** Updated asset type.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/asset-types/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if not found.

---

## 2. Assets (CRUD)

**url:** `{{baseurl}}/adminapi/assets/`  
**method:** GET  
**body:** None  
**sample_response:** Array of asset objects (with asset_type, status as related).  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/assets/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single asset.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/assets/`  
**method:** POST  
**body:** Asset fields per AssetSerializer.  
**sample_response:** Created asset. 201.  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/assets/<id>/`  
**method:** PUT or PATCH  
**body:** Asset fields (partial for PATCH).  
**sample_response:** Updated asset.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/assets/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if not found.

---

## 3. Bill category (CRUD)

**url:** `{{baseurl}}/adminapi/billCategory/`  
**method:** GET  
**body:** None  
**sample_response:** Array of bill category objects.  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/billCategory/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single bill category.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/billCategory/`  
**method:** POST  
**body:** Bill category fields.  
**sample_response:** Created category. 201.  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/billCategory/<id>/`  
**method:** PUT or PATCH  
**body:** Category fields (partial for PATCH).  
**sample_response:** Updated category.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/billCategory/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if not found.

---

## 4. Bills (CRUD)

**url:** `{{baseurl}}/adminapi/bills/`  
**method:** GET  
**body:** None  
**sample_response:** Array of bill objects (category, status as related).  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/bills/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single bill.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/bills/`  
**method:** POST  
**body:** Bill fields per BillSerializer.  
**sample_response:** Created bill. 201.  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/bills/<id>/`  
**method:** PUT or PATCH  
**body:** Bill fields (partial for PATCH).  
**sample_response:** Updated bill.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/bills/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if not found.

---

## 5. Expenses (CRUD)

**url:** `{{baseurl}}/adminapi/expenses/`  
**method:** GET  
**body:** None  
**sample_response:** Array of expense tracker objects (status as related).  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/expenses/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single expense.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/expenses/`  
**method:** POST  
**body:** Expense fields per ExpenseTrackerSerializer.  
**sample_response:** Created expense. 201.  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/expenses/<id>/`  
**method:** PUT or PATCH  
**body:** Expense fields (partial for PATCH).  
**sample_response:** Updated expense.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/expenses/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if not found.

---

## 6. Vendors (CRUD)

**url:** `{{baseurl}}/adminapi/vendors/`  
**method:** GET  
**body:** None  
**sample_response:** Array of vendor objects.  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/vendors/<id>/`  
**method:** GET  
**body:** None  
**sample_response:** Single vendor.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/vendors/`  
**method:** POST  
**body:** Vendor fields per VendorSerializer.  
**sample_response:** Created vendor. 201.  
**notes:** AdminPermission.

---

**url:** `{{baseurl}}/adminapi/vendors/<id>/`  
**method:** PUT or PATCH  
**body:** Vendor fields (partial for PATCH).  
**sample_response:** Updated vendor.  
**notes:** 404 if not found.

---

**url:** `{{baseurl}}/adminapi/vendors/<id>/`  
**method:** DELETE  
**body:** None  
**sample_response:** 204 No Content.  
**notes:** 404 if not found.

---

## 7. Dashboard summary

**url:** `{{baseurl}}/adminapi/dashboard/`  
**method:** GET  
**body:** None  
**sample_response:**
```json
{
  "assets": {
    "total": 50,
    "by_type": [
      { "asset_type__name": "Laptop", "count": 30 },
      { "asset_type__name": "Monitor", "count": 20 }
    ]
  },
  "bills": {
    "total_amount": 100000,
    "by_category": [
      { "category__name": "Utilities", "total": 50000 }
    ]
  },
  "expense_tracker": { "total_amount": 25000 },
  "vendors": { "total": 10 }
}
```
**notes:** AdminPermission. Aggregated counts and amounts for assets, bills, expenses, vendors.
