import json
from decimal import Decimal, InvalidOperation

from accounts.filters import _get_user_role_sync
from accounts.snippet import csrf_exempt, login_required
from django.db import transaction
from ems.RequiredImports import HttpRequest, JsonResponse, status, sync_to_async
from ems.utils import gmt_to_ist_str
from ems.verify_methods import (
    load_data,
    verifyDelete,
    verifyGet,
    verifyPatch,
    verifyPost,
    verifyPut,
)

from .models import CustomerPanelAmountLog, CustomerPanelEntry


def _is_admin_or_md(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    role = _get_user_role_sync(user)
    return role in ("Admin", "MD")


def _coerce_decimal(raw, field_name):
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number") from None
    if not value.is_finite():
        raise ValueError(f"{field_name} must be a finite number")
    return value


def _calc_total(value, tax_percent):
    if value is None:
        return None
    tax = tax_percent if tax_percent is not None else Decimal("0")
    return value + (value * tax / Decimal("100"))


def _entry_to_dict(obj: CustomerPanelEntry):
    created_by_username = None
    if getattr(obj, "created_by", None) is not None:
        created_by_username = getattr(obj.created_by, "username", None)
        if created_by_username is not None:
            created_by_username = str(created_by_username)
    return {
        "id": obj.id,
        "business_name": obj.business_name,
        "office_address": obj.office_address,
        "representative_name": obj.representative_name,
        "representative_contact_number": obj.representative_contact_number,
        "serial_no": obj.serial_no,
        "product": obj.product,
        "service": obj.service,
        "date": str(obj.date) if obj.date else None,
        "value": float(obj.value) if obj.value is not None else None,
        "tax_percent": float(obj.tax_percent) if obj.tax_percent is not None else None,
        "total": float(obj.total) if obj.total is not None else None,
        # Keep created_by as username string for frontend display.
        "created_by": created_by_username,
        "created_at": gmt_to_ist_str(obj.created_at, "%d/%m/%Y %H:%M:%S") if obj.created_at else None,
        "updated_at": gmt_to_ist_str(obj.updated_at, "%d/%m/%Y %H:%M:%S") if obj.updated_at else None,
    }


def _amount_log_to_dict(obj: CustomerPanelAmountLog):
    return {
        "id": obj.id,
        "entry_id": obj.entry_id,
        "amount": float(obj.amount),
        "date": str(obj.date),
        "notes": obj.notes,
        "created_at": gmt_to_ist_str(obj.created_at, "%d/%m/%Y %H:%M:%S") if obj.created_at else None,
        "updated_at": gmt_to_ist_str(obj.updated_at, "%d/%m/%Y %H:%M:%S") if obj.updated_at else None,
    }


def _list_entries_sync():
    qs = CustomerPanelEntry.objects.select_related("created_by").order_by("-created_at")
    return [_entry_to_dict(obj) for obj in qs]


def _create_entry_sync(user, data):
    business_name = str(data.get("business_name") or "").strip()
    if not business_name:
        raise ValueError("business_name is required")
    value = _coerce_decimal(data.get("value"), "value")
    tax_percent = _coerce_decimal(data.get("tax_percent"), "tax_percent")
    total = _calc_total(value, tax_percent)
    return CustomerPanelEntry.objects.create(
        business_name=business_name,
        office_address=data.get("office_address"),
        representative_name=data.get("representative_name"),
        representative_contact_number=data.get("representative_contact_number"),
        serial_no=data.get("serial_no"),
        product=data.get("product"),
        service=data.get("service"),
        date=data.get("date") or None,
        value=value,
        tax_percent=tax_percent,
        total=total,
        created_by=user,
    )


def _get_entry_sync(entry_id):
    return CustomerPanelEntry.objects.select_related("created_by").get(id=entry_id)


def _update_entry_sync(entry_id, data):
    obj = CustomerPanelEntry.objects.get(id=entry_id)
    if "business_name" in data:
        name = str(data.get("business_name") or "").strip()
        if not name:
            raise ValueError("business_name cannot be empty")
        obj.business_name = name
    for field in [
        "office_address",
        "representative_name",
        "representative_contact_number",
        "serial_no",
        "product",
        "service",
        "date",
    ]:
        if field in data:
            val = data.get(field)
            if field == "date" and val == "":
                val = None
            setattr(obj, field, val)
    value_changed = "value" in data
    tax_changed = "tax_percent" in data
    if value_changed:
        obj.value = _coerce_decimal(data.get("value"), "value")
    if tax_changed:
        obj.tax_percent = _coerce_decimal(data.get("tax_percent"), "tax_percent")
    if value_changed or tax_changed:
        obj.total = _calc_total(obj.value, obj.tax_percent)
    obj.save()
    return obj


@csrf_exempt
@login_required
async def list_create_entries(request: HttpRequest):
    if not await sync_to_async(_is_admin_or_md)(request.user):
        return JsonResponse({"error": "Only Admin/MD can access customer panel"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        if verifyGet(request):
            return verifyGet(request)
        data = await sync_to_async(_list_entries_sync)()
        return JsonResponse(data, safe=False)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        obj = await sync_to_async(_create_entry_sync)(request.user, data)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    payload = _entry_to_dict(obj)
    payload["message"] = "Customer panel entry created"
    return JsonResponse(payload, status=status.HTTP_201_CREATED)


@csrf_exempt
@login_required
async def detail_update_delete_entry(request: HttpRequest, entry_id: int):
    if not await sync_to_async(_is_admin_or_md)(request.user):
        return JsonResponse({"error": "Only Admin/MD can access customer panel"}, status=status.HTTP_403_FORBIDDEN)
    try:
        obj = await sync_to_async(_get_entry_sync)(entry_id)
    except CustomerPanelEntry.DoesNotExist:
        return JsonResponse({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        if verifyGet(request):
            return verifyGet(request)
        return JsonResponse(_entry_to_dict(obj), status=status.HTTP_200_OK)

    if request.method in ("PUT", "PATCH"):
        err = verifyPut(request) if request.method == "PUT" else verifyPatch(request)
        if err:
            return err
        try:
            data = load_data(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            obj = await sync_to_async(_update_entry_sync)(entry_id, data)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({"message": "Customer panel entry updated", "id": obj.id}, status=status.HTTP_200_OK)

    if request.method == "DELETE":
        if verifyDelete(request):
            return verifyDelete(request)
        await sync_to_async(obj.delete)()
        return JsonResponse({"message": "Customer panel entry deleted"}, status=status.HTTP_200_OK)

    return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


def _ensure_entry_exists_sync(entry_id):
    return CustomerPanelEntry.objects.get(id=entry_id)


def _list_amount_logs_sync(entry_id):
    qs = CustomerPanelAmountLog.objects.filter(entry_id=entry_id).order_by("-date", "-created_at")
    return [_amount_log_to_dict(obj) for obj in qs]


def _create_amount_logs_sync(entry_id, items):
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty array")

    to_create = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"items[{idx}] must be an object")
        amount = _coerce_decimal(item.get("amount"), "amount")
        if amount is None:
            raise ValueError(f"items[{idx}].amount is required")
        date_value = item.get("date")
        if date_value is None or (isinstance(date_value, str) and not date_value.strip()):
            raise ValueError(f"items[{idx}].date is required")
        notes = item.get("notes")
        to_create.append(
            CustomerPanelAmountLog(
                entry_id=entry_id,
                amount=amount,
                date=date_value,
                notes=notes,
            )
        )

    with transaction.atomic():
        created = CustomerPanelAmountLog.objects.bulk_create(to_create)
    return created


@csrf_exempt
@login_required
async def amount_log_list_create(request: HttpRequest, entry_id: int):
    if not await sync_to_async(_is_admin_or_md)(request.user):
        return JsonResponse({"error": "Only Admin/MD can access customer panel"}, status=status.HTTP_403_FORBIDDEN)

    try:
        await sync_to_async(_ensure_entry_exists_sync)(entry_id)
    except CustomerPanelEntry.DoesNotExist:
        return JsonResponse({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        if verifyGet(request):
            return verifyGet(request)
        data = await sync_to_async(_list_amount_logs_sync)(entry_id)
        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

    items = data.get("items")
    try:
        created = await sync_to_async(_create_amount_logs_sync)(entry_id, items)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return JsonResponse(
        {
            "message": "Amount logs created",
            "count": len(created),
            "ids": [obj.id for obj in created],
        },
        status=status.HTTP_201_CREATED,
    )


def _update_amount_log_sync(entry_id, log_id, data):
    obj = CustomerPanelAmountLog.objects.get(id=log_id, entry_id=entry_id)
    if "amount" in data:
        amount = _coerce_decimal(data.get("amount"), "amount")
        if amount is None:
            raise ValueError("amount cannot be empty")
        obj.amount = amount
    if "date" in data:
        date_value = data.get("date")
        if date_value is None or (isinstance(date_value, str) and not date_value.strip()):
            raise ValueError("date cannot be empty")
        obj.date = date_value
    if "notes" in data:
        obj.notes = data.get("notes")
    obj.save()
    return obj


def _delete_amount_log_sync(entry_id, log_id):
    obj = CustomerPanelAmountLog.objects.get(id=log_id, entry_id=entry_id)
    obj.delete()


@csrf_exempt
@login_required
async def amount_log_detail_update_delete(request: HttpRequest, entry_id: int, log_id: int):
    if not await sync_to_async(_is_admin_or_md)(request.user):
        return JsonResponse({"error": "Only Admin/MD can access customer panel"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "PATCH":
        err = verifyPatch(request)
        if err:
            return err
        try:
            data = load_data(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            obj = await sync_to_async(_update_amount_log_sync)(entry_id, log_id, data)
        except CustomerPanelAmountLog.DoesNotExist:
            return JsonResponse({"error": "Amount log not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({"message": "Amount log updated", "id": obj.id}, status=status.HTTP_200_OK)

    if request.method == "DELETE":
        if verifyDelete(request):
            return verifyDelete(request)
        try:
            await sync_to_async(_delete_amount_log_sync)(entry_id, log_id)
        except CustomerPanelAmountLog.DoesNotExist:
            return JsonResponse({"error": "Amount log not found"}, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse({"message": "Amount log deleted"}, status=status.HTTP_200_OK)

    return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

