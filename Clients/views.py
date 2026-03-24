"""
Client Lead API - Add Client Lead form.
No database changes. Uses existing ClientProfile, CurrentClientStage, ClientProfileMembers.
"""
import json
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db.models import Prefetch, Q, F
from ems.RequiredImports import sync_to_async, JsonResponse, status, HttpRequest
from ems.verify_methods import verifyGet, verifyPost, verifyPut, verifyPatch, verifyDelete, load_data
from ems.utils import gmt_to_ist_str
from accounts.snippet import login_required, csrf_exempt
from accounts.models import User
from .models import (
    ClientProfile,
    CurrentClientStage,
    ClientProfileMembers,
    ClientConversation,
    ClientInteractionChannels,
)
from project.models import Project, Product
from QuaterlyReports.models import SalesStatistics
from task_management.models import TaskStatus


# Medium names that map to SalesStatistics count fields (must match ClientInteractionChannels: Calls, Trial, Demand, Pitch)
SALES_STAT_MEDIUM_FIELDS = {"calls": "Calls", "trial": "Trial", "demand": "Demand", "pitch": "Pitch"}


def _increment_sales_stat_for_conversation_sync(client, medium_name):
    """
    When a conversation is added with a medium (Calls, Trial, Demand, Pitch), increment
    the corresponding SalesStatistics count for the client's product and today's date.
    Uses unique_together (product, date); creates row with status PENDING if missing.
    """
    if not medium_name or not isinstance(medium_name, str):
        return
    key = medium_name.strip().lower()
    field_name = SALES_STAT_MEDIUM_FIELDS.get(key)
    if not field_name:
        return
    # Resolve client's Product (Project) to project.Product by name
    client_product = getattr(client, "Product", None)
    if not client_product:
        return
    product = Product.objects.filter(name=client_product.name).first()
    if not product:
        return
    today = timezone.now().date()
    pending = TaskStatus.objects.filter(status_name__iexact="PENDING").first()
    if not pending:
        return
    defaults = {
        "status": pending,
        "Conversion_percent": Decimal("0"),
        "Calls": 0,
        "Trial": 0,
        "Demand": 0,
        "Pitch": 0,
    }
    stat, _ = SalesStatistics.objects.get_or_create(
        product=product,
        date=today,
        defaults=defaults,
    )
    update_kw = {field_name: F(field_name) + 1}
    SalesStatistics.objects.filter(pk=stat.pk).update(**update_kw)


def _product_list_sync():
    """Fetch all products from database (id, name) for dropdown."""
    return list(Product.objects.all().order_by("name").values("id", "name"))


# ==================== Products (from database) ====================
# URL: {{baseurl}}/clientsapi/products/  | GET
@login_required
async def product_list(request: HttpRequest):
    """GET /clientsapi/products/ — product list (id, name) for dropdown. Auth required."""
    if verifyGet(request):
        return verifyGet(request)
    data = await sync_to_async(_product_list_sync)()
    return JsonResponse(data, safe=False)


# ==================== Employees list ====================
# URL: {{baseurl}}/clientsapi/employees/  | GET
def _get_employees_sync():
    users = User.objects.all().values("id", "username")
    return list(users)


@login_required
async def employee_list(request: HttpRequest):
    """GET /clientsapi/employees/ - All users for employee checkboxes."""
    if verifyGet(request):
        return verifyGet(request)
    data = await sync_to_async(_get_employees_sync)()
    return JsonResponse(data, safe=False)


# ==================== Stages ====================
def _get_stages_sync():
    stages = CurrentClientStage.objects.all().values("id", "name")
    return list(stages)


@login_required
async def stage_list(request: HttpRequest):
    """GET /clientsapi/stages/ - Pipeline stages for status dropdown."""
    if verifyGet(request):
        return verifyGet(request)
    data = await sync_to_async(_get_stages_sync)()
    return JsonResponse(data, safe=False)


# ==================== Client Profile CRUD ====================
def _user_can_access_profile(user, profile):
    """True if user is the profile creator or a member of the profile. Uses prefetched members when available to avoid extra query."""
    if not user or not profile:
        return False
    if profile.created_by_id == user.pk:
        return True
    prefetched = getattr(profile, "_prefetched_objects_cache", {}).get("members")
    if prefetched is not None:
        return any(m.pk == user.pk for m in prefetched)
    return ClientProfileMembers.objects.filter(client_profile=profile, user=user).exists()


def _get_user_display_name(u):
    """Return Profile.Name, or first_name + last_name, or username as fallback."""
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


def _coerce_product_value(raw):
    """
    Parse API product_value to Decimal for DB. None / empty → None.
    Raises ValueError if a non-empty value is not a valid finite number.
    """
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    try:
        d = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("product_value must be a valid number") from None
    if not d.is_finite():
        raise ValueError("product_value must be a finite number")
    return d


def _product_value_for_json(c):
    """JSON-serializable product_value (float) or None."""
    if c.product_value is None:
        return None
    return float(c.product_value)


def _note_to_dict(conv):
    return {
        "id": conv.id,
        "note": conv.note,
        "created_by": conv.created_by.username if conv.created_by else None,
        "created_at": gmt_to_ist_str(conv.created_at, "%d/%m/%Y %H:%M:%S") if conv.created_at else None,
        "medium": getattr(conv.medium, "medium", None),
    }


def _profile_to_dict(c):
    notes = [_note_to_dict(conv) for conv in c.conversations.all()] if hasattr(c, "conversations") else []
    return {
        "id": c.id,
        "company_name": c.company_name,
        "client_name": c.client_name,
        "client_contact": c.client_contact,
        "representative_contact_number": c.representative_contact_number,
        "representative_name": c.representative_name,
        "motive": getattr(c, "motive", "") or "",
        "gst_number": c.gst_number,
        "status_id": c.status_id,
        "status_name": c.status.name if c.status else None,
        "product_id": c.Product_id,
        "product_name": c.Product.name if c.Product else None,
        "product_value": _product_value_for_json(c),
        "created_by": c.created_by.username if c.created_by else None,
        "members": [_get_user_display_name(u) for u in c.members.all()],
        "notes": notes,
        "created_at": gmt_to_ist_str(c.created_at, "%d/%m/%Y %H:%M:%S") if c.created_at else None,
        "updated_at": gmt_to_ist_str(c.updated_at, "%d/%m/%Y %H:%M:%S") if c.updated_at else None,
    }


def _list_profiles_sync(user):
    """List only profiles the user is allowed to access (creator or member)."""
    conv_prefetch = Prefetch(
        "conversations",
        queryset=ClientConversation.objects.select_related("created_by", "medium").order_by("-created_at"),
    )
    members_prefetch = Prefetch(
        "members",
        queryset=User.objects.select_related("accounts_profile"),
    )
    qs = (
        ClientProfile.objects.filter(Q(created_by=user) | Q(member_links__user=user))
        .distinct()
        .select_related("status", "Product", "created_by")
        .prefetch_related(members_prefetch, conv_prefetch)
        .order_by("-created_at")
    )
    return [_profile_to_dict(c) for c in qs]


@csrf_exempt
@login_required
async def profile_list_create(request: HttpRequest):
    """GET /clientsapi/profiles/ - List (only profiles user created or is member of). POST - Create."""
    if request.method == "GET":
        if verifyGet(request):
            return verifyGet(request)
        data = await sync_to_async(_list_profiles_sync)(request.user)
        return JsonResponse(data, safe=False)
    return await profile_create(request)


def _get_profile_sync(profile_id):
    conv_prefetch = Prefetch(
        "conversations",
        queryset=ClientConversation.objects.select_related("created_by", "medium").order_by("-created_at"),
    )
    members_prefetch = Prefetch(
        "members",
        queryset=User.objects.select_related("accounts_profile"),
    )
    return ClientProfile.objects.select_related("status", "Product", "created_by").prefetch_related(
        members_prefetch, conv_prefetch
    ).get(id=profile_id)


@csrf_exempt
@login_required
async def profile_detail_update_delete(request: HttpRequest, profile_id: int):
    """GET /profiles/<id>/ - Detail. PUT/PATCH - Update. DELETE - Delete. Access: creator or member only."""
    try:
        c = await sync_to_async(_get_profile_sync)(profile_id)
    except ClientProfile.DoesNotExist:
        return JsonResponse({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_profile)(request.user, c):
        return JsonResponse({"error": "You do not have access to this client profile"}, status=status.HTTP_403_FORBIDDEN)
    if request.method == "GET":
        if verifyGet(request):
            return verifyGet(request)
        return JsonResponse(_profile_to_dict(c))
    if request.method in ("PUT", "PATCH"):
        return await profile_update(request, profile_id)
    if request.method == "DELETE":
        return await profile_delete(request, profile_id)
    return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


def _get_profile_with_members_sync(profile_id):
    """Fetch profile with members and their profiles in one go. Use for both access check and member list."""
    members_prefetch = Prefetch(
        "members",
        queryset=User.objects.select_related("accounts_profile"),
    )
    return ClientProfile.objects.select_related("created_by").prefetch_related(members_prefetch).get(id=profile_id)


def _get_profile_members_sync(profile_id):
    """List member display names for profile. Prefer using _get_profile_with_members_sync + c.members.all() to avoid duplicate query."""
    members_prefetch = Prefetch(
        "members",
        queryset=User.objects.select_related("accounts_profile"),
    )
    c = ClientProfile.objects.prefetch_related(members_prefetch).get(id=profile_id)
    return [_get_user_display_name(u) for u in c.members.all()]


@login_required
async def profile_members(request: HttpRequest, profile_id: int):
    """GET /clientsapi/profiles/<id>/members/ - Selected employees for this client. Access: creator or member only. Single query + prefetch."""
    if verifyGet(request):
        return verifyGet(request)
    try:
        c = await sync_to_async(_get_profile_with_members_sync)(profile_id)
    except ClientProfile.DoesNotExist:
        return JsonResponse({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_profile)(request.user, c):
        return JsonResponse({"error": "You do not have access to this client profile"}, status=status.HTTP_403_FORBIDDEN)
    data = [_get_user_display_name(u) for u in c.members.all()]
    return JsonResponse(data, safe=False)


def _get_user_from_member(m):
    """Resolve member value (id or username) to User. Tries id first, then username as fallback."""
    uid = m.get("id") if isinstance(m, dict) else m
    uname = m.get("username") if isinstance(m, dict) else (m if isinstance(m, str) else None)
    u = None
    if uid is not None and uid != "":
        try:
            pid = int(uid) if (isinstance(uid, str) and str(uid).replace("-", "").isdigit()) else uid
            u = User.objects.get(id=pid)
        except (User.DoesNotExist, TypeError, ValueError):
            try:
                u = User.objects.get(username=str(uid))
            except User.DoesNotExist:
                pass
    if u is None and uname:
        try:
            u = User.objects.get(username=str(uname))
        except User.DoesNotExist:
            pass
    return u


def _create_profile_sync(user, data):
    status_obj = None
    if data.get("status_id"):
        try:
            status_obj = CurrentClientStage.objects.get(id=data["status_id"])
        except CurrentClientStage.DoesNotExist:
            pass
    if not status_obj:
        try:
            status_obj = CurrentClientStage.objects.get(name="Leads")
        except CurrentClientStage.DoesNotExist:
            pass

    product_obj = None
    product_name = data.get("product_name") or data.get("Product") or data.get("product")
    if product_name:
        product_obj = Project.objects.filter(name__iexact=str(product_name).strip()).first()

    product_value = None
    if "product_value" in data:
        product_value = _coerce_product_value(data.get("product_value"))

    c = ClientProfile.objects.create(
        company_name=data.get("company_name", ""),
        client_name=data.get("client_name", ""),
        client_contact=data.get("client_contact", ""),
        representative_contact_number=data.get("representative_contact_number", ""),
        representative_name=data.get("representative_name", ""),
        motive=data.get("motive", "") or data.get("description", ""),
        gst_number=data.get("gst_number", ""),
        status=status_obj,
        Product=product_obj,
        product_value=product_value,
        created_by=user,
    )

    members = data.get("members", []) or data.get("employees", [])
    for m in members:
        u = _get_user_from_member(m)
        if u:
            ClientProfileMembers.objects.get_or_create(client_profile=c, user=u)

    return c


@csrf_exempt
@login_required
async def profile_create(request: HttpRequest):
    """POST /clientsapi/profiles/ - Create client lead."""
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    if not data.get("company_name") or not data.get("client_name"):
        return JsonResponse(
            {"error": "company_name and client_name are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        c = await sync_to_async(_create_profile_sync)(request.user, data)
        return JsonResponse({"id": c.id, "message": "Client lead created"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def _update_profile_sync(profile_id, data):
    c = ClientProfile.objects.get(id=profile_id)
    if "company_name" in data:
        c.company_name = data["company_name"]
    if "client_name" in data:
        c.client_name = data["client_name"]
    if "client_contact" in data:
        c.client_contact = data["client_contact"]
    if "representative_contact_number" in data:
        c.representative_contact_number = data["representative_contact_number"]
    if "representative_name" in data:
        c.representative_name = data["representative_name"]
    if "motive" in data:
        c.motive = data["motive"]
    if "description" in data:
        c.motive = data["description"]
    if "gst_number" in data:
        c.gst_number = data["gst_number"]
    if "status_id" in data:
        try:
            c.status = CurrentClientStage.objects.get(id=data["status_id"])
        except CurrentClientStage.DoesNotExist:
            pass
    if "product_name" in data or "product" in data or "Product" in data:
        pn = data.get("product_name") or data.get("product") or data.get("Product")
        if pn:
            c.Product = Project.objects.filter(name__iexact=str(pn).strip()).first()
        else:
            c.Product = None
    if "product_value" in data:
        c.product_value = _coerce_product_value(data.get("product_value"))
    if "members" in data or "employees" in data:
        members = data.get("members", data.get("employees", []))
        c.members.clear()
        for m in members:
            u = _get_user_from_member(m)
            if u:
                ClientProfileMembers.objects.get_or_create(client_profile=c, user=u)
    c.save()
    return c


@csrf_exempt
@login_required
async def profile_update(request: HttpRequest, profile_id: int):
    """PUT/PATCH /clientsapi/profiles/<id>/ - Update client lead. Access: creator or member only."""
    if request.method == "PUT":
        err = verifyPut(request)
    elif request.method == "PATCH":
        err = verifyPatch(request)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    if err:
        return err
    try:
        data = load_data(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        c = await sync_to_async(ClientProfile.objects.get)(id=profile_id)
    except ClientProfile.DoesNotExist:
        return JsonResponse({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_profile)(request.user, c):
        return JsonResponse({"error": "You do not have access to this client profile"}, status=status.HTTP_403_FORBIDDEN)
    try:
        await sync_to_async(_update_profile_sync)(profile_id, data)
        return JsonResponse({"message": "Client lead updated"}, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@login_required
async def profile_delete(request: HttpRequest, profile_id: int):
    """DELETE /clientsapi/profiles/<id>/ - Delete client lead. Access: creator or member only."""
    if verifyDelete(request):
        return verifyDelete(request)
    try:
        c = await sync_to_async(ClientProfile.objects.get)(id=profile_id)
    except ClientProfile.DoesNotExist:
        return JsonResponse({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_profile)(request.user, c):
        return JsonResponse({"error": "You do not have access to this client profile"}, status=status.HTTP_403_FORBIDDEN)
    await sync_to_async(c.delete)()
    return JsonResponse({"message": "Client lead deleted"}, status=status.HTTP_200_OK)


# ==================== Notes (Conversations) ====================
def _list_conversations_sync(profile_id):
    convs = ClientConversation.objects.filter(client_id=profile_id).select_related("created_by", "medium").order_by("-created_at")
    return [_note_to_dict(c) for c in convs]


def _get_client_sync(profile_id):
    """Fetch client profile. Optimized: select_related created_by, prefetch members for access check without extra queries."""
    return ClientProfile.objects.select_related("created_by").prefetch_related("members").get(id=profile_id)


@csrf_exempt
@login_required
async def conversation_list_create(request: HttpRequest, profile_id: int):
    """GET /profiles/<id>/conversations/ - List notes. POST - Add note. Access: creator or member only."""
    try:
        client = await sync_to_async(_get_client_sync)(profile_id)
    except ClientProfile.DoesNotExist:
        return JsonResponse({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_profile)(request.user, client):
        return JsonResponse({"error": "You do not have access to this client profile"}, status=status.HTTP_403_FORBIDDEN)
    if request.method == "GET":
        if verifyGet(request):
            return verifyGet(request)
        data = await sync_to_async(_list_conversations_sync)(profile_id)
        return JsonResponse(data, safe=False)
    if request.method == "POST":
        if verifyPost(request):
            return verifyPost(request)
        try:
            data = load_data(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
        # client already fetched and access checked above
        def _create_many(client, note_list, user, medium_obj):
            ids = []
            for note_text in note_list:
                txt = str(note_text).strip() if note_text else ""
                if txt:
                    conv = ClientConversation.objects.create(client=client, note=txt, created_by=user, medium=medium_obj)
                    ids.append(conv.id)
            return ids

        if "notes" in data and isinstance(data["notes"], list):
            note_list = [n for n in data["notes"] if n]
            if not note_list:
                return JsonResponse({"error": "notes array cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
            # Optional channel medium name; match by full name (case-insensitive).
            medium_name = str(data.get("medium", "")).strip() if data.get("medium") else None
            medium_obj = None
            if medium_name:
                medium_obj = await sync_to_async(ClientInteractionChannels.objects.filter(medium__iexact=medium_name).first)()
                if medium_obj is None:
                    return JsonResponse({"error": "Invalid medium"}, status=status.HTTP_400_BAD_REQUEST)
            ids = await sync_to_async(_create_many)(client, note_list, request.user, medium_obj)
            if medium_name:
                await sync_to_async(_increment_sales_stat_for_conversation_sync)(client, medium_name)
            return JsonResponse({"ids": ids, "message": f"{len(ids)} note(s) added"}, status=status.HTTP_201_CREATED)
        note_text = data.get("note", "").strip()
        if not note_text:
            return JsonResponse({"error": "note or notes is required"}, status=status.HTTP_400_BAD_REQUEST)

        def _create_one(client, note_text, user, medium_obj):
            return ClientConversation.objects.create(client=client, note=note_text, created_by=user, medium=medium_obj)

        medium_name = str(data.get("medium", "")).strip() if data.get("medium") else None
        medium_obj = None
        if medium_name:
            medium_obj = await sync_to_async(ClientInteractionChannels.objects.filter(medium__iexact=medium_name).first)()
            if medium_obj is None:
                return JsonResponse({"error": "Invalid medium"}, status=status.HTTP_400_BAD_REQUEST)

        conv = await sync_to_async(_create_one)(client, note_text, request.user, medium_obj)
        if medium_name:
            await sync_to_async(_increment_sales_stat_for_conversation_sync)(client, medium_name)
        return JsonResponse({"id": conv.id, "message": "Note added"}, status=status.HTTP_201_CREATED)
    return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


def _update_note_sync(profile_id, note_id, data):
    conv = ClientConversation.objects.get(id=note_id, client_id=profile_id)
    if "note" in data:
        conv.note = str(data["note"]).strip() or conv.note
    conv.save()


def _delete_note_sync(profile_id, note_id):
    conv = ClientConversation.objects.get(id=note_id, client_id=profile_id)
    conv.delete()


@csrf_exempt
@login_required
async def conversation_update_delete(request: HttpRequest, profile_id: int, note_id: int):
    """PATCH /profiles/<id>/conversations/<note_id>/ - Update note. DELETE - Delete note. Access: creator or member only."""
    try:
        profile = await sync_to_async(ClientProfile.objects.get)(id=profile_id)
    except ClientProfile.DoesNotExist:
        return JsonResponse({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)
    if not await sync_to_async(_user_can_access_profile)(request.user, profile):
        return JsonResponse({"error": "You do not have access to this client profile"}, status=status.HTTP_403_FORBIDDEN)
    if request.method == "PATCH":
        err = verifyPatch(request)
        if err:
            return err
        try:
            data = load_data(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            await sync_to_async(_update_note_sync)(profile_id, note_id, data)
        except ClientConversation.DoesNotExist:
            return JsonResponse({"error": "Note not found"}, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse({"message": "Note updated"}, status=status.HTTP_200_OK)
    if request.method == "DELETE":
        if verifyDelete(request):
            return verifyDelete(request)
        try:
            await sync_to_async(_delete_note_sync)(profile_id, note_id)
        except ClientConversation.DoesNotExist:
            return JsonResponse({"error": "Note not found"}, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse({"message": "Note deleted"}, status=status.HTTP_200_OK)
    return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


