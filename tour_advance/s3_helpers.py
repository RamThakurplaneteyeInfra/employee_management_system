import mimetypes
import os
import uuid
from urllib.parse import unquote, urlparse

from django.conf import settings

from ems.s3_utils import get_presigned_url, get_s3_client

from .models import TOUR_ADVANCE_S3_PREFIX, TOUR_ADVANCE_S3_PREFIX_LEGACY

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB
ALLOWED_EXTENSIONS = (
    "pdf",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "txt",
)

_ALLOWED_KEY_PREFIXES = (
    TOUR_ADVANCE_S3_PREFIX,
    TOUR_ADVANCE_S3_PREFIX_LEGACY,
    "files/tour_advance",
)


def _allowed_prefixes_with_slash():
    return tuple(p.strip("/").replace("\\", "/") + "/" for p in _ALLOWED_KEY_PREFIXES)


def normalize_s3_key_from_client(value):
    """
    Accept a storage key or a full S3/HTTPS URL and return a normalized key.
    """
    if not value or not isinstance(value, str):
        return ""
    s = unquote(value.strip().replace("\\", "/"))
    if not s:
        return ""
    path = s
    if s.lower().startswith(("http://", "https://")):
        path = (urlparse(s).path or "").lstrip("/")

    for prefix in _allowed_prefixes_with_slash():
        folder = prefix.rstrip("/")
        key = f"{folder}/"
        idx = path.find(key)
        if idx >= 0:
            return path[idx:].lstrip("/")
        idx = s.find(key)
        if idx >= 0:
            return s[idx:].lstrip("/")
    return path.lstrip("/")


def upload_tour_advance_file(file_obj):
    """Upload to S3 under Billing_Attachment/ and return the S3 key."""
    ext = ""
    name = getattr(file_obj, "name", "") or ""
    if "." in name:
        ext = "." + name.rsplit(".", 1)[-1].lower()
    prefix = TOUR_ADVANCE_S3_PREFIX.strip("/").replace("\\", "/")
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


def validate_upload_file(file_obj):
    if not file_obj:
        return "No file provided"
    try:
        size = int(getattr(file_obj, "size", 0) or 0)
    except Exception:
        size = 0
    if size <= 0:
        return "Empty file is not allowed"
    if size > MAX_UPLOAD_BYTES:
        return f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
    name = (getattr(file_obj, "name", "") or "").strip()
    if "." not in name:
        return "File extension is required."
    ext = name.rsplit(".", 1)[-1].lower()
    if ext not in set(ALLOWED_EXTENSIONS):
        return f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    return None


def is_allowed_s3_key(s3_key):
    if not s3_key or not isinstance(s3_key, str):
        return False
    key = normalize_s3_key_from_client(s3_key)
    if not key or ".." in key or key.startswith(("/", "\\")):
        return False
    for prefix in _allowed_prefixes_with_slash():
        if key.startswith(prefix):
            return True
    return False


def attachment_read_payload(
    s3_key, file_name="", file_type="", file_size=0, amount=None, attachment_id=None
):
    key = (s3_key or "").replace("\\", "/")
    display_name = file_name or os.path.basename(key) or "file"
    content_type = file_type or ""
    if not content_type:
        guessed, _ = mimetypes.guess_type(display_name)
        content_type = guessed or "application/octet-stream"
    payload = {
        "fileName": display_name,
        "fileType": content_type,
        "fileSize": int(file_size or 0),
        "fileUrl": get_presigned_url(key),
        "s3Key": key,
        "amount": str(amount if amount is not None else 0),
    }
    if attachment_id is not None:
        payload["id"] = attachment_id
    return payload


def upload_response_payload(file_obj, s3_key):
    file_name = os.path.basename(s3_key.replace("\\", "/")) or (
        getattr(file_obj, "name", "file") or "file"
    )
    content_type = getattr(file_obj, "content_type", "") or ""
    if not content_type:
        guessed, _ = mimetypes.guess_type(file_name)
        content_type = guessed or "application/octet-stream"
    file_size = getattr(file_obj, "size", None) or 0
    return {
        "fileName": getattr(file_obj, "name", file_name) or file_name,
        "fileType": content_type,
        "fileSize": file_size,
        "fileUrl": s3_key,
        "s3Key": s3_key,
        "amount": "0",
    }
