"""
Admin panel API views. Base path: {{baseurl}}/adminapi/
- ViewSets (CRUD): asset-types, assets, billCategory, bills, expenses, expense-categories,
  expense-advances, vendors. AdminPermission.
- GET /dashboard/ — summary counts/amounts for assets, bills, expenses, vendors.
- GET /expenses/month_summary/?year=&month= — advance, spent, remaining for that month.
- GET /expenses/?year=&month= — filter list by paid_date (optional).
"""
from decimal import Decimal
import mimetypes
import os
import uuid

from django.conf import settings
from django.db.models import Count, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ems.s3_utils import get_presigned_url, get_s3_client
from .models import (
    AssetType,
    Asset,
    Bill,
    BillCategory,
    ExpenseCategory,
    ExpenseMonthlyAdvance,
    ExpenseTracker,
    Vendor,
)
from .permissions import AdminPermission
from .models import (
    ADMIN_S3_BILL_PREFIX,
    ADMIN_S3_EXPENSE_PREFIX,
    ADMIN_S3_VENDOR_PREFIX,
    _DOCUMENT_ATTACHMENT_EXTENSIONS,
)
from .serializers import (
    AssetTypeSerializer,
    AssetSerializer,
    BillCategorySerializer,
    BillSerializer,
    ExpenseCategorySerializer,
    ExpenseMonthlyAdvanceSerializer,
    ExpenseTrackerSerializer,
    VendorSerializer,
)

# Note: DRF ViewSets do not support async methods - they don't await coroutines.
# Sync views work under ASGI; Django runs them in a thread pool automatically.

_MAX_ADMIN_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB (keep aligned with adminpanel.serializers)


def _upload_admin_attachment_to_s3(file_obj, key_prefix: str) -> str:
    """
    Upload a Django UploadedFile to S3 under a fixed prefix and return the S3 key.
    Uses the same AWS creds/bucket as ems.s3_utils.get_s3_client.
    """
    # Ensure we keep extension only (server-side validation also checks allowed extensions).
    ext = ""
    name = getattr(file_obj, "name", "") or ""
    if "." in name:
        ext = "." + name.rsplit(".", 1)[-1].lower()
    prefix = (key_prefix or "").strip("/").replace("\\", "/")
    key = f"{prefix}/{uuid.uuid4().hex}{ext}"

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    if not bucket:
        raise ValueError("AWS_STORAGE_BUCKET_NAME is not set")

    client = get_s3_client()
    extra = {}
    ctype = getattr(file_obj, "content_type", None) or None
    if ctype:
        extra["ContentType"] = ctype
    client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra)
    return key


def _upload_file_response_payload(file_obj, s3_key: str):
    file_name = os.path.basename(s3_key.replace("\\", "/")) or (getattr(file_obj, "name", "file") or "file")
    content_type = getattr(file_obj, "content_type", "") or ""
    if not content_type:
        guessed, _ = mimetypes.guess_type(file_name)
        content_type = guessed or "application/octet-stream"
    file_size = getattr(file_obj, "size", None)
    url = get_presigned_url(s3_key)
    return {
        "id": uuid.uuid4().hex,  # ephemeral id (messaging uses a DB id; here we keep API shape without new tables)
        "s3_key": s3_key,
        "file_name": getattr(file_obj, "name", file_name) or file_name,
        "content_type": content_type,
        "file_size": file_size,
        "url": url,
    }


def _validate_admin_upload_file(file_obj):
    if not file_obj:
        return "No file provided"
    try:
        size = int(getattr(file_obj, "size", 0) or 0)
    except Exception:
        size = 0
    if size <= 0:
        return "Empty file is not allowed"
    if size > _MAX_ADMIN_UPLOAD_BYTES:
        return f"File too large. Maximum size is {_MAX_ADMIN_UPLOAD_BYTES // (1024 * 1024)} MB."
    name = (getattr(file_obj, "name", "") or "").strip()
    if "." not in name:
        return "File extension is required."
    ext = name.rsplit(".", 1)[-1].lower()
    if ext not in set(_DOCUMENT_ATTACHMENT_EXTENSIONS):
        return f"Invalid file type. Allowed: {', '.join(_DOCUMENT_ATTACHMENT_EXTENSIONS)}"
    return None


# ==================== AssetTypeViewSet ====================
# URL: {{baseurl}}/adminapi/asset-types/  | List, Create, Retrieve, Update, Delete
class AssetTypeViewSet(viewsets.ModelViewSet):
    queryset = AssetType.objects.all()
    serializer_class = AssetTypeSerializer
    permission_classes = [IsAuthenticated,AdminPermission]


# ==================== AssetViewSet ====================
# URL: {{baseurl}}/adminapi/assets/  | CRUD
class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related("asset_type", "status")
    serializer_class = AssetSerializer
    permission_classes = [AdminPermission]


# ==================== BillCategoryViewSet ====================
# URL: {{baseurl}}/adminapi/billCategory/  | CRUD
class BillCategoryViewSet(viewsets.ModelViewSet):
    queryset = BillCategory.objects.filter()
    serializer_class = BillCategorySerializer
    permission_classes = [AdminPermission]


# ==================== BillViewSet ====================
# URL: {{baseurl}}/adminapi/bills/  | CRUD
class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.select_related("category", "status")
    serializer_class = BillSerializer
    permission_classes = [AdminPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    # Upload-only endpoint (messaging-style): POST /adminapi/bills/uploadFile/ with multipart field "file"
    @action(detail=False, methods=["post"], url_path="uploadFile", parser_classes=[MultiPartParser, FormParser])
    def uploadFile(self, request):
        file_obj = request.FILES.get("file")
        err = _validate_admin_upload_file(file_obj)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        try:
            s3_key = _upload_admin_attachment_to_s3(file_obj, ADMIN_S3_BILL_PREFIX)
        except Exception as e:
            return Response({"error": f"Upload failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(_upload_file_response_payload(file_obj, s3_key), status=status.HTTP_201_CREATED)


# ==================== ExpenseCategoryViewSet ====================
# URL: {{baseurl}}/adminapi/expense-categories/  | CRUD (dropdown + add new)
class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [AdminPermission]


# ==================== ExpenseMonthlyAdvanceViewSet ====================
# URL: {{baseurl}}/adminapi/expense-advances/  | CRUD (one advance per year+month)
class ExpenseMonthlyAdvanceViewSet(viewsets.ModelViewSet):
    queryset = ExpenseMonthlyAdvance.objects.all()
    serializer_class = ExpenseMonthlyAdvanceSerializer
    permission_classes = [AdminPermission]


# ==================== ExpenseTrackerViewSet ====================
# URL: {{baseurl}}/adminapi/expenses/  | CRUD
# Optional query: ?year=2026&month=4 filters by expense paid_date
class ExpenseTrackerViewSet(viewsets.ModelViewSet):
    queryset = ExpenseTracker.objects.select_related("status", "category")
    serializer_class = ExpenseTrackerSerializer
    permission_classes = [AdminPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = super().get_queryset()
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        if year is not None and str(year).strip() != "":
            try:
                qs = qs.filter(paid_date__year=int(year))
            except (TypeError, ValueError):
                pass
        if month is not None and str(month).strip() != "":
            try:
                m = int(month)
                if 1 <= m <= 12:
                    qs = qs.filter(paid_date__month=m)
            except (TypeError, ValueError):
                pass
        return qs

    @action(detail=False, methods=["get"], url_path="month_summary")
    def month_summary(self, request):
        """Advance for the month, total spent (by paid_date), remaining, and count."""
        year = request.query_params.get("year")
        month = request.query_params.get("month")
        if year is None or month is None or str(year).strip() == "" or str(month).strip() == "":
            return Response(
                {"detail": "Query parameters year and month are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            y, m = int(year), int(month)
        except (TypeError, ValueError):
            return Response({"detail": "year and month must be integers."}, status=status.HTTP_400_BAD_REQUEST)
        if m < 1 or m > 12:
            return Response({"detail": "month must be between 1 and 12."}, status=status.HTTP_400_BAD_REQUEST)

        advance_row = ExpenseMonthlyAdvance.objects.filter(year=y, month=m).first()
        advance_amount = advance_row.advance_amount if advance_row else Decimal("0")

        agg = ExpenseTracker.objects.filter(paid_date__year=y, paid_date__month=m).aggregate(
            total=Sum("amount"),
            count=Count("id"),
        )
        total_spent = agg["total"] or Decimal("0")
        remaining = advance_amount - total_spent

        return Response(
            {
                "year": y,
                "month": m,
                "advance_amount": str(advance_amount),
                "total_spent": str(total_spent),
                "remaining": str(remaining),
                "expense_count": agg["count"] or 0,
                "advance_note": advance_row.note if advance_row else "",
            }
        )

    # Upload-only endpoint (messaging-style): POST /adminapi/expenses/uploadFile/ with multipart field "file"
    @action(detail=False, methods=["post"], url_path="uploadFile", parser_classes=[MultiPartParser, FormParser])
    def uploadFile(self, request):
        file_obj = request.FILES.get("file")
        err = _validate_admin_upload_file(file_obj)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        try:
            s3_key = _upload_admin_attachment_to_s3(file_obj, ADMIN_S3_EXPENSE_PREFIX)
        except Exception as e:
            return Response({"error": f"Upload failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(_upload_file_response_payload(file_obj, s3_key), status=status.HTTP_201_CREATED)


# ==================== VendorViewSet ====================
# URL: {{baseurl}}/adminapi/vendors/  | CRUD
class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [AdminPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    # Upload-only endpoint (messaging-style): POST /adminapi/vendors/uploadFile/ with multipart field "file"
    @action(detail=False, methods=["post"], url_path="uploadFile", parser_classes=[MultiPartParser, FormParser])
    def uploadFile(self, request):
        file_obj = request.FILES.get("file")
        err = _validate_admin_upload_file(file_obj)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        try:
            s3_key = _upload_admin_attachment_to_s3(file_obj, ADMIN_S3_VENDOR_PREFIX)
        except Exception as e:
            return Response({"error": f"Upload failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(_upload_file_response_payload(file_obj, s3_key), status=status.HTTP_201_CREATED)


# ==================== dashboard_summary ====================
# Dashboard summary (assets, bills, expenses, vendors).
# URL: {{baseurl}}/adminapi/dashboard/
# Method: GET

@api_view(['GET'])
@permission_classes([AdminPermission])
def dashboard_summary(request):
    """Sync view - DRF's @api_view doesn't properly await async functions."""
    assets_total = Asset.objects.count()
    assets_by_type = Asset.objects.values('asset_type__name').annotate(count=Count('id'))
    bills_total = Bill.objects.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
    bills_by_category = Bill.objects.values('category__name').annotate(total=Sum('amount'))
    expenses_total = ExpenseTracker.objects.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
    vendors_total = Vendor.objects.count()
    data = {
        "assets": {"total": assets_total, "by_type": list(assets_by_type)},
        "bills": {"total_amount": bills_total, "by_category": list(bills_by_category)},
        "expense_tracker": {"total_amount": expenses_total},
        "vendors": {"total": vendors_total},
    }
    return Response(data)