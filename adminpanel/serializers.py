import base64
import mimetypes
import os
import re
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import serializers
from task_management.models import TaskStatus

from ems.s3_utils import get_presigned_url
from .models import (
    ADMIN_S3_BILL_PREFIX,
    ADMIN_S3_EXPENSE_PREFIX,
    ADMIN_S3_VENDOR_PREFIX,
    AssetType,
    Asset,
    Bill,
    BillCategory,
    BillFloor,
    ExpenseCategory,
    ExpenseMonthlyAdvance,
    ExpenseTracker,
    Vendor,
)

# Align with model FileExtensionValidator; cap size to limit abuse (DoS / storage).
_MAX_ADMIN_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB

# data:mime;base64,...  (whitespace in base64 allowed)
_DATA_URL_RE = re.compile(
    r"^data:(?P<mime>[\w/+\-.]+);base64,(?P<b64>[\s\S]+)$",
    re.IGNORECASE | re.DOTALL,
)

# Legacy: *_attachments/<32 hex>.<ext>  New: Attachment/Bill|Vendor|Expense/<32 hex>.<ext>
_SAFE_STORED_NAME_RE = re.compile(
    r"^(?:(?:vendor_attachments|bill_attachments|expense_attachments)|"
    r"Attachment/(?:Bill|Vendor|Expense))/[0-9a-f]{32}\.[_a-zA-Z0-9.]+$"
)


def _storage_name_from_client_media_string(s, allowed_stored_path_prefixes):
    """
    Resolve a string the client re-sent (absolute media URL, /media/... path, or storage
    name) to a single storage-relative name. Only allows whitelisted folder prefixes; no
    '..' or remote URL fetches (SSRF).
    """
    if not allowed_stored_path_prefixes:
        raise serializers.ValidationError("Server configuration error: no allowed path prefixes.")
    s = unquote(s.strip().replace("\\", "/"))
    if not s:
        return None
    path = s
    if s.lower().startswith(("http://", "https://")):
        path = (urlparse(s).path or "").replace("\\", "/")

    def _try_extract(candidate: str):
        candidate = candidate.replace("\\", "/")
        for pfx in allowed_stored_path_prefixes:
            folder = pfx.rstrip("/")
            key = f"{folder}/"
            i = candidate.find(key)
            if i >= 0:
                return candidate[i:].lstrip("/")
        return None

    rel = _try_extract(path) or _try_extract(s)
    if not rel:
        raise serializers.ValidationError(
            "Attachment URL or path is not a recognized file under this field's allowed storage."
        )
    if ".." in rel or rel.startswith(("/", "\\")) or "//" in rel:
        raise serializers.ValidationError("Invalid attachment path.")
    for part in rel.split("/"):
        if part in (".", "..", ""):
            raise serializers.ValidationError("Invalid attachment path.")
    allowed = tuple(pfx.rstrip("/") + "/" for pfx in allowed_stored_path_prefixes)
    if not any(rel.startswith(p) for p in allowed):
        raise serializers.ValidationError("Attachment is not in an allowed folder for this field.")
    if not _SAFE_STORED_NAME_RE.match(rel):
        raise serializers.ValidationError(
            "Only previously uploaded document names under allowed folders "
            "(e.g. bill_attachments/<id>.pdf or Attachment/Bill/<id>.pdf) are accepted."
        )
    if not default_storage.exists(rel):
        raise serializers.ValidationError("That file is not present in storage (or was removed).")
    return rel


class MultipartOrDataUrlFileField(serializers.FileField):
    """
    Accepts: multipart file, base64 data URL, a full URL or /media/... string pointing at an
    existing file in allowed storage (same server), or null/empty to clear.

    The URL path reuses an existing object in default storage (no re-upload, no new uuid name).
    """

    def __init__(self, *args, allowed_stored_path_prefixes=None, **kwargs):
        if allowed_stored_path_prefixes is not None and not isinstance(
            allowed_stored_path_prefixes, (tuple, list)
        ):
            raise TypeError("allowed_stored_path_prefixes must be a tuple or list of strings")
        # Default: allow both app folders; prefer passing explicit per-serializer prefixes.
        self.allowed_stored_path_prefixes = tuple(allowed_stored_path_prefixes) if (
            allowed_stored_path_prefixes is not None
        ) else (
            "vendor_attachments/",
            "bill_attachments/",
            "expense_attachments/",
            f"{ADMIN_S3_VENDOR_PREFIX}/",
            f"{ADMIN_S3_BILL_PREFIX}/",
            f"{ADMIN_S3_EXPENSE_PREFIX}/",
        )
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        if data in (None,):
            if not self.allow_null:
                raise serializers.ValidationError("This field may not be null.")
            return None
        if data == "":
            return None
        if isinstance(data, str):
            s = data.strip()
            if not s:
                return None
            if s.lower().startswith("data:"):
                return self._content_file_from_data_url(s)
            return _storage_name_from_client_media_string(
                s, self.allowed_stored_path_prefixes
            )
        return super().to_internal_value(data)

    def _content_file_from_data_url(self, s: str) -> ContentFile:
        m = _DATA_URL_RE.match(s.strip())
        if not m:
            raise serializers.ValidationError(
                "Invalid data URL. Use data:<mime>;base64,<encoded data> (e.g. data:application/pdf;base64,...)."
            )
        b64 = re.sub(r"\s+", "", m.group("b64"))
        try:
            raw = base64.b64decode(b64, validate=True)
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid base64 in data URL.")
        if len(raw) > _MAX_ADMIN_UPLOAD_BYTES:
            raise serializers.ValidationError(
                f"File too large. Maximum size is {_MAX_ADMIN_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
        mime = m.group("mime").split(";")[0].lower().strip()
        ext = mimetypes.guess_extension(mime, strict=False) or ".bin"
        if ext in (".jpe", ".jpeg"):
            ext = ".jpg"
        if ext == ".mpga":
            ext = ".mp3"
        # Avoid odd dual extensions from guess_extension
        name = f"upload{ext}"
        return ContentFile(raw, name=name)


def _admin_attachment_read_url(attachment, request):
    """
    Public read URL for an optional FileField: presigned GET when S3 is configured
    (same bucket/keys as django-storages for these models), else FieldFile.url.
    """
    if not attachment or not getattr(attachment, "name", None):
        return None
    if (
        getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        and getattr(settings, "AWS_ACCESS_KEY_ID", None)
    ):
        presigned = get_presigned_url(attachment.name)
        if presigned:
            return presigned
    try:
        url = attachment.url
    except Exception:
        return None
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if request is not None:
        return request.build_absolute_uri(url)
    return url


def _admin_attachment_payload(attachment, request):
    """
    Messaging-style attachment object for JSON responses (read only).
    Keys match messaging upload response: s3_key, file_name, content_type, file_size, url.
    """
    if not attachment or not getattr(attachment, "name", None):
        return None
    name = attachment.name.replace("\\", "/")
    file_name = os.path.basename(name) or "file"
    ctype, _ = mimetypes.guess_type(file_name)
    if not ctype:
        ctype = "application/octet-stream"
    try:
        fsize = int(attachment.size)
    except Exception:
        fsize = 0
    return {
        "s3_key": name,
        "file_name": file_name,
        "content_type": ctype,
        "file_size": fsize,
        "url": _admin_attachment_read_url(attachment, request),
    }


class _AdminFileAttachmentResponseMixin:
    """
    On read, represent attachment as an object (like messaging) instead of a bare file URL string.
    Writes are unchanged: multipart file, data URL, or storage path string.
    """

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["attachment"] = _admin_attachment_payload(
            instance.attachment, self.context.get("request")
        )
        return ret


# 1 AssetType Serializer (Dropdown)
class AssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetType
        fields = ['id', 'name']

# 2 Asset Serializer
class AssetSerializer(serializers.ModelSerializer):
    asset_type = serializers.SlugRelatedField(
        queryset=AssetType.objects.all(),
        slug_field="name"
    )
    status= serializers.SlugRelatedField(
        queryset=TaskStatus.objects.all(),
        slug_field="status_name")

    class Meta:
        model = Asset
        fields = [
            'id',
            'asset_type',
            'asset_name',
            'author',
            'asset_code',
            'created_at',
            'updated_at',
            'status'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
# 3 Bill Category
class BillCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BillCategory
        fields = ['id', 'name']


# 4 Bills
class BillSerializer(_AdminFileAttachmentResponseMixin, serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        queryset=BillCategory.objects.all(),
        slug_field="name"
    )
    status = serializers.SlugRelatedField(
        queryset=TaskStatus.objects.all(),
        slug_field="status_name")
    floor = serializers.ChoiceField(
        choices=BillFloor.choices,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def validate_floor(self, value):
        if value in (None, ""):
            return None
        return value

    attachment = MultipartOrDataUrlFileField(
        required=False,
        allow_null=True,
        allow_empty_file=False,
        allowed_stored_path_prefixes=(
            "bill_attachments/",
            f"{ADMIN_S3_BILL_PREFIX}/",
        ),
    )

    class Meta:
        model = Bill
        fields = [
            "id",
            "category",
            "amount",
            "recipient",
            "floor",
            "attachment",
            "created_at",
            "status",
            "date",
        ]
        read_only_fields = ["created_at"]

    def validate_attachment(self, value):
        if not value:
            return value
        if isinstance(value, str):
            try:
                sz = default_storage.size(value)
            except Exception:
                raise serializers.ValidationError("Could not read attachment from storage.")
            if sz > _MAX_ADMIN_UPLOAD_BYTES:
                raise serializers.ValidationError(
                    f"File too large. Maximum size is {_MAX_ADMIN_UPLOAD_BYTES // (1024 * 1024)} MB."
                )
            return value
        if value.size > _MAX_ADMIN_UPLOAD_BYTES:
            raise serializers.ValidationError(
                f"File too large. Maximum size is {_MAX_ADMIN_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
        return value


# 5a Expense category (dropdown; same pattern as BillCategory)
class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "created_at"]
        read_only_fields = ["created_at"]


# 5b Monthly advance (one row per calendar month)
class ExpenseMonthlyAdvanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseMonthlyAdvance
        fields = ["id", "year", "month", "advance_amount", "note", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate_month(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError("Month must be between 1 and 12.")
        return value

    def validate_year(self, value):
        if value < 1900 or value > 3000:
            raise serializers.ValidationError("Year is out of allowed range.")
        return value

    def validate(self, attrs):
        year = attrs.get("year", getattr(self.instance, "year", None))
        month = attrs.get("month", getattr(self.instance, "month", None))
        if year is None or month is None:
            return attrs
        qs = ExpenseMonthlyAdvance.objects.filter(year=year, month=month)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"non_field_errors": ["An advance for this year and month already exists. Update that record instead."]}
            )
        return attrs


class VendorExpenseField(serializers.Field):
    """Accept vendor id (number/string) or business_name on write; emit vendor id on read."""

    def to_internal_value(self, data):
        if data is None or data == "":
            return None
        if isinstance(data, bool):
            raise serializers.ValidationError("Vendor must be a valid id or business name.")
        if isinstance(data, int) or (isinstance(data, str) and str(data).strip().isdigit()):
            pk = int(data)
            try:
                return Vendor.objects.get(pk=pk)
            except Vendor.DoesNotExist as exc:
                raise serializers.ValidationError(
                    f"Vendor with id={pk} does not exist."
                ) from exc
        name = str(data).strip()
        if not name:
            return None
        try:
            return Vendor.objects.get(business_name=name)
        except Vendor.DoesNotExist as exc:
            raise serializers.ValidationError(
                f"Vendor with business_name={name} does not exist."
            ) from exc

    def to_representation(self, value):
        return value.pk if value else None


class VendorDropdownSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="business_name", read_only=True)

    class Meta:
        model = Vendor
        fields = ["id", "name"]


# 5 Expense Tracker
class ExpenseTrackerSerializer(_AdminFileAttachmentResponseMixin, serializers.ModelSerializer):
    status = serializers.SlugRelatedField(
        queryset=TaskStatus.objects.all(),
        slug_field="status_name",
    )
    category = serializers.SlugRelatedField(
        slug_field="name",
        queryset=ExpenseCategory.objects.all(),
        required=False,
        allow_null=True,
    )
    vendor = VendorExpenseField(required=False, allow_null=True)
    vendor_name = serializers.SerializerMethodField()
    attachment = MultipartOrDataUrlFileField(
        required=False,
        allow_null=True,
        allow_empty_file=False,
        allowed_stored_path_prefixes=(
            "expense_attachments/",
            f"{ADMIN_S3_EXPENSE_PREFIX}/",
        ),
    )

    class Meta:
        model = ExpenseTracker
        fields = [
            "id",
            "title",
            "amount",
            "note",
            "category",
            "vendor",
            "vendor_name",
            "attachment",
            "paid_date",
            "created_at",
            "status",
        ]
        read_only_fields = ["created_at", "vendor_name"]

    def get_vendor_name(self, obj):
        vendor = getattr(obj, "vendor", None)
        return vendor.business_name if vendor else None

    def validate_attachment(self, value):
        if not value:
            return value
        if isinstance(value, str):
            try:
                sz = default_storage.size(value)
            except Exception:
                raise serializers.ValidationError("Could not read attachment from storage.")
            if sz > _MAX_ADMIN_UPLOAD_BYTES:
                raise serializers.ValidationError(
                    f"File too large. Maximum size is {_MAX_ADMIN_UPLOAD_BYTES // (1024 * 1024)} MB."
                )
            return value
        if value.size > _MAX_ADMIN_UPLOAD_BYTES:
            raise serializers.ValidationError(
                f"File too large. Maximum size is {_MAX_ADMIN_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
        return value


# 6 Vendor
class VendorSerializer(_AdminFileAttachmentResponseMixin, serializers.ModelSerializer):
    total_service_price = serializers.SerializerMethodField()
    expense_count = serializers.SerializerMethodField()
    attachment = MultipartOrDataUrlFileField(
        required=False,
        allow_null=True,
        allow_empty_file=False,
        allowed_stored_path_prefixes=(
            "vendor_attachments/",
            f"{ADMIN_S3_VENDOR_PREFIX}/",
        ),
    )

    class Meta:
        model = Vendor
        fields = [
            'id',
            'business_name',
            'gst_number',
            'office_address',
            'email',
            'primary_phone',
            'alternate_phone',
            'service',
            'total_service_price',
            'expense_count',
            'attachment',
            'created_at',
        ]
        read_only_fields = ['created_at', 'total_service_price', 'expense_count']

    def get_total_service_price(self, obj):
        val = getattr(obj, "total_service_price", None)
        if val is None:
            return "0.00"
        return format(val, ".2f")

    def get_expense_count(self, obj):
        count = getattr(obj, "expense_count", None)
        return count or 0

    def validate_attachment(self, value):
        if not value:
            return value
        if isinstance(value, str):
            try:
                sz = default_storage.size(value)
            except Exception:
                raise serializers.ValidationError("Could not read attachment from storage.")
            if sz > _MAX_ADMIN_UPLOAD_BYTES:
                raise serializers.ValidationError(
                    f"File too large. Maximum size is {_MAX_ADMIN_UPLOAD_BYTES // (1024 * 1024)} MB."
                )
            return value
        if value.size > _MAX_ADMIN_UPLOAD_BYTES:
            raise serializers.ValidationError(
                f"File too large. Maximum size is {_MAX_ADMIN_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
        return value

    def validate_service(self, value):
        if value is None:
            return ""
        text = value.strip()
        if len(text) > 10000:
            raise serializers.ValidationError(
                "Service description must be at most 10000 characters."
            )
        return text

