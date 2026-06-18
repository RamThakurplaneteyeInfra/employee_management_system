import json
from decimal import Decimal, InvalidOperation

from accounts.filters import _get_user_role_sync
from accounts.models import User
from accounts.snippet import csrf_exempt, login_required
from django.db import transaction
from django.db.models import Count, DecimalField, OuterRef, Prefetch, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from ems.RequiredImports import HttpRequest, JsonResponse, status, sync_to_async
from ems.utils import gmt_to_ist_str, get_user_from_member
from ems.verify_methods import (
    load_data,
    verifyDelete,
    verifyGet,
    verifyPatch,
    verifyPost,
    verifyPut,
)

from .models import CustomerPanelAmountLog, CustomerPanelEntry, CustomerPanelEntryMembers

_VALID_DIVISIONS = frozenset(
    {CustomerPanelEntry.DIVISION_FARM, CustomerPanelEntry.DIVISION_INFRA}
)
_LEDGER_DIVISION_FILTERS = frozenset({"farm", "infra", "others"})


def _is_admin_or_md(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    role = _get_user_role_sync(user)
    return role in ("Admin", "MD")


def _is_md(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _get_user_role_sync(user) == "MD"


def _user_can_access_entry(user, entry: CustomerPanelEntry) -> bool:
    """Admin / MD / superuser: any entry. Others: creator or a selected member."""
    if not user or not user.is_authenticated:
        return False
    if _is_admin_or_md(user):
        return True
    if entry.created_by_id == user.id:
        return True
    prefetched = getattr(entry, "_prefetched_objects_cache", {}).get("members")
    if prefetched is not None:
        return any(m.pk == user.id for m in prefetched)
    return CustomerPanelEntryMembers.objects.filter(entry=entry, user=user).exists()


def _get_user_display_name(u):
    """Match Clients profile members endpoint: Profile.Name, or first+last, or username."""
    try:
        profile = getattr(u, "accounts_profile", None)
        if profile and getattr(profile, "Name", None):
            return profile.Name
    except Exception:
        pass
    first = getattr(u, "first_name", None) or ""
    last = getattr(u, "last_name", None) or ""
    full = f"{first} {last}".strip()
    return full or u.username


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


def _parse_division(raw, *, required=False):
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        if required:
            raise ValueError("division is required")
        return None
    value = str(raw).strip().lower()
    if value not in _VALID_DIVISIONS:
        raise ValueError("division must be 'farm' or 'infra'")
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
    # Members: {id, username} per record — aligns with client lead detail JSON style.
    members_payload = [{"id": u.id, "username": u.username} for u in obj.members.all()]
    return {
        "id": obj.id,
        "business_name": obj.business_name,
        "client_name": obj.client_name,
        "client_contact": obj.client_contact,
        "office_address": obj.office_address,
        "representative_name": obj.representative_name,
        "representative_contact_number": obj.representative_contact_number,
        "serial_no": obj.serial_no,
        "product": obj.product,
        "division": obj.division,
        "service": obj.service,
        "date": str(obj.date) if obj.date else None,
        "value": float(obj.value) if obj.value is not None else None,
        "tax_percent": float(obj.tax_percent) if obj.tax_percent is not None else None,
        "total": float(obj.total) if obj.total is not None else None,
        # Keep created_by as username string for frontend display.
        "created_by": created_by_username,
        "members": members_payload,
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


def _summary_totals_for_scope(entry_qs, log_qs):
    zero = Value(Decimal("0"), output_field=DecimalField())
    entry_agg = entry_qs.aggregate(
        entry_count=Count("id"),
        total_amount=Coalesce(Sum("total"), zero),
    )
    paid_agg = log_qs.aggregate(paid=Coalesce(Sum("amount"), zero))
    total_amount = entry_agg["total_amount"] or Decimal("0")
    paid = paid_agg["paid"] or Decimal("0")
    return {
        "entry_count": entry_agg["entry_count"] or 0,
        "total_amount": float(total_amount),
        "paid": float(paid),
        "remaining": float(total_amount - paid),
    }


def _entries_summary_sync():
    all_entries = CustomerPanelEntry.objects.all()
    all_logs = CustomerPanelAmountLog.objects.all()
    summary = _summary_totals_for_scope(all_entries, all_logs)
    summary["distribution"] = {
        "farm": _summary_totals_for_scope(
            all_entries.filter(division=CustomerPanelEntry.DIVISION_FARM),
            all_logs.filter(entry__division=CustomerPanelEntry.DIVISION_FARM),
        ),
        "infra": _summary_totals_for_scope(
            all_entries.filter(division=CustomerPanelEntry.DIVISION_INFRA),
            all_logs.filter(entry__division=CustomerPanelEntry.DIVISION_INFRA),
        ),
        "others": _summary_totals_for_scope(
            all_entries.filter(division__isnull=True),
            all_logs.filter(entry__division__isnull=True),
        ),
    }
    return summary


class _QueryParamsAdapter:
    """Adapt Django HttpRequest for leave_scoring helpers that expect query_params."""

    def __init__(self, request: HttpRequest):
        self.query_params = request.GET
        self.user = request.user


def _entries_points_sync(request: HttpRequest):
    from accounts.leave_views import _get_user_role_sync, _user_can_view_on_leave
    from accounts.leave_scoring import parse_leave_points_period, resolve_leave_points_user

    from .customer_panel_scoring import build_customer_panel_entries_points

    adapted = _QueryParamsAdapter(request)
    year, month, quarter, period_err = parse_leave_points_period(adapted)
    if period_err is not None:
        return {"error": period_err.get("detail", "Invalid period.")}, status.HTTP_400_BAD_REQUEST

    target_user, user_err = resolve_leave_points_user(
        adapted, _user_can_view_on_leave, _get_user_role_sync
    )
    if user_err is not None:
        err_status = (
            status.HTTP_404_NOT_FOUND
            if "not found" in user_err["detail"].lower()
            else status.HTTP_403_FORBIDDEN
        )
        return {"error": user_err["detail"]}, err_status

    return build_customer_panel_entries_points(target_user, year, month=month, quarter=quarter), status.HTTP_200_OK


@csrf_exempt
@login_required
async def entries_points(request: HttpRequest):
    """
    Customer panel entry performance points (MMR/RG only).
    GET /customerpanelapi/entries/points/?year=2026&month=6
    ₹5,00,000 entered in a month = 40 main points (₹12,500 per point); excess as bonus.
    Optional: ?employee=<username> (HR / Admin / MD / TeamLead for team members)
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    if verifyGet(request):
        return verifyGet(request)
    data, code = await sync_to_async(_entries_points_sync)(request)
    if code != status.HTTP_200_OK:
        return JsonResponse(data, status=code)
    return JsonResponse(data, status=code)


def _entries_queryset_for_user(user):
    qs = CustomerPanelEntry.objects.all().order_by("-created_at")
    if not _is_admin_or_md(user):
        qs = qs.filter(Q(created_by=user) | Q(members=user)).distinct()
    return qs


def _entry_paid_subquery():
    """Per-entry payment sum; avoids M2M join inflation when filtering by members."""
    return (
        CustomerPanelAmountLog.objects.filter(entry_id=OuterRef("pk"))
        .values("entry_id")
        .annotate(total_paid=Sum("amount"))
        .values("total_paid")
    )


def _list_entries_ledger_sync(user, division_filter=None):
    zero = Value(Decimal("0"), output_field=DecimalField())
    qs = _entries_queryset_for_user(user).annotate(
        paid=Coalesce(Subquery(_entry_paid_subquery()), zero),
    )
    if division_filter == "farm":
        qs = qs.filter(division=CustomerPanelEntry.DIVISION_FARM)
    elif division_filter == "infra":
        qs = qs.filter(division=CustomerPanelEntry.DIVISION_INFRA)
    elif division_filter == "others":
        qs = qs.filter(division__isnull=True)

    rows = []
    for obj in qs:
        total = float(obj.total) if obj.total is not None else 0.0
        paid = float(obj.paid or 0)
        rows.append(
            {
                "id": obj.id,
                "business_name": obj.business_name,
                "client_name": obj.client_name,
                "total": total,
                "paid": paid,
                "remaining": total - paid,
            }
        )
    return rows


def _list_entries_sync(user):
    members_prefetch = Prefetch(
        "members",
        queryset=User.objects.only("id", "username"),
    )
    qs = (
        _entries_queryset_for_user(user)
        .select_related("created_by")
        .prefetch_related(members_prefetch)
    )
    return [_entry_to_dict(obj) for obj in qs]


def _apply_members_to_entry(entry, raw_list):
    if not raw_list:
        return
    for m in raw_list:
        u = get_user_from_member(m)
        if u:
            CustomerPanelEntryMembers.objects.get_or_create(entry=entry, user=u)


def _create_entry_sync(user, data):
    business_name = str(data.get("business_name") or "").strip()
    if not business_name:
        raise ValueError("business_name is required")
    value = _coerce_decimal(data.get("value"), "value")
    tax_percent = _coerce_decimal(data.get("tax_percent"), "tax_percent")
    total = _calc_total(value, tax_percent)
    division = _parse_division(data.get("division"), required=True)
    obj = CustomerPanelEntry.objects.create(
        business_name=business_name,
        client_name=data.get("client_name"),
        client_contact=data.get("client_contact"),
        office_address=data.get("office_address"),
        representative_name=data.get("representative_name"),
        representative_contact_number=data.get("representative_contact_number"),
        serial_no=data.get("serial_no"),
        product=data.get("product"),
        division=division,
        service=data.get("service"),
        date=data.get("date") or None,
        value=value,
        tax_percent=tax_percent,
        total=total,
        created_by=user,
    )
    members = data.get("members", []) or data.get("employees", [])
    _apply_members_to_entry(obj, members)
    return _get_entry_sync(obj.id)


def _get_entry_sync(entry_id):
    members_prefetch = Prefetch(
        "members",
        queryset=User.objects.only("id", "username"),
    )
    return (
        CustomerPanelEntry.objects.select_related("created_by")
        .prefetch_related(members_prefetch)
        .get(id=entry_id)
    )


def _get_entry_for_members_endpoint_sync(entry_id):
    members_prefetch = Prefetch(
        "members",
        queryset=User.objects.select_related("accounts_profile"),
    )
    return (
        CustomerPanelEntry.objects.select_related("created_by")
        .prefetch_related(members_prefetch)
        .get(id=entry_id)
    )


def _update_entry_sync(entry_id, data):
    obj = CustomerPanelEntry.objects.select_related("created_by").prefetch_related("members").get(id=entry_id)
    if "business_name" in data:
        name = str(data.get("business_name") or "").strip()
        if not name:
            raise ValueError("business_name cannot be empty")
        obj.business_name = name
    if "division" in data:
        obj.division = _parse_division(data.get("division"), required=True)
    for field in [
        "client_name",
        "client_contact",
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
    if "members" in data or "employees" in data:
        members = data.get("members", data.get("employees", []))
        obj.members.clear()
        _apply_members_to_entry(obj, members)
    return _get_entry_sync(entry_id)


@csrf_exempt
@login_required
async def entries_ledger(request: HttpRequest):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    if verifyGet(request):
        return verifyGet(request)
    division = (request.GET.get("division") or "").strip().lower()
    if division and division not in _LEDGER_DIVISION_FILTERS:
        return JsonResponse(
            {"error": "division must be 'farm', 'infra', or 'others'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    data = await sync_to_async(_list_entries_ledger_sync)(
        request.user,
        division_filter=division or None,
    )
    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)


@csrf_exempt
@login_required
async def entries_summary(request: HttpRequest):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    if verifyGet(request):
        return verifyGet(request)
    if not _is_md(request.user):
        return JsonResponse({"error": "Only MD can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)
    data = await sync_to_async(_entries_summary_sync)()
    return JsonResponse(data, status=status.HTTP_200_OK)


@csrf_exempt
@login_required
async def list_create_entries(request: HttpRequest):
    if request.method == "GET":
        if verifyGet(request):
            return verifyGet(request)
        data = await sync_to_async(_list_entries_sync)(request.user)
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
    try:
        obj = await sync_to_async(_get_entry_sync)(entry_id)
    except CustomerPanelEntry.DoesNotExist:
        return JsonResponse({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_entry)(request.user, obj):
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


@csrf_exempt
@login_required
async def entry_members(request: HttpRequest, entry_id: int):
    """GET .../entries/<id>/members/ — same shape as Clients profile_members (display names JSON array)."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    if verifyGet(request):
        return verifyGet(request)
    try:
        entry = await sync_to_async(_get_entry_for_members_endpoint_sync)(entry_id)
    except CustomerPanelEntry.DoesNotExist:
        return JsonResponse({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_entry)(request.user, entry):
        return JsonResponse({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    data = [_get_user_display_name(u) for u in entry.members.all()]
    return JsonResponse(data, safe=False)


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
    try:
        entry = await sync_to_async(_get_entry_sync)(entry_id)
    except CustomerPanelEntry.DoesNotExist:
        return JsonResponse({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_entry)(request.user, entry):
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
    try:
        entry = await sync_to_async(_get_entry_sync)(entry_id)
    except CustomerPanelEntry.DoesNotExist:
        return JsonResponse({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_entry)(request.user, entry):
        return JsonResponse({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)

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

