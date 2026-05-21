"""S3 upload helpers for employee certificates (Certificate/ prefix only)."""
import uuid
from urllib.parse import unquote, urlparse

from django.conf import settings

from ems.s3_utils import get_presigned_url, get_s3_client

from .models import CERTIFICATE_S3_PREFIX

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB
ALLOWED_EXTENSIONS = frozenset(
    {"pdf", "jpg", "jpeg", "png", "gif", "webp", "doc", "docx"}
)


def certificate_s3_prefix():
    raw = getattr(settings, "AWS_S3_CERTIFICATE_PREFIX", None) or CERTIFICATE_S3_PREFIX
    return raw.strip("/").replace("\\", "/")


def _allowed_prefix_with_slash():
    return certificate_s3_prefix() + "/"


def normalize_s3_key_from_client(value):
    """Accept storage key or HTTPS S3 URL; return normalized key under Certificate/."""
    if not value or not isinstance(value, str):
        return ""
    s = unquote(value.strip().replace("\\", "/"))
    if not s:
        return ""
    path = s
    if s.lower().startswith(("http://", "https://")):
        path = (urlparse(s).path or "").lstrip("/")
    prefix = _allowed_prefix_with_slash()
    folder = prefix.rstrip("/")
    key = f"{folder}/"
    for candidate in (path, s):
        idx = candidate.find(key)
        if idx >= 0:
            return candidate[idx:].lstrip("/")
    return path.lstrip("/")


def is_allowed_s3_key(key):
    if not key:
        return False
    normalized = key.lstrip("/").replace("\\", "/")
    return normalized.startswith(_allowed_prefix_with_slash())


def validate_upload_file(file_obj):
    if not file_obj:
        return "No file provided"
    size = getattr(file_obj, "size", None)
    if size is not None and size > MAX_UPLOAD_BYTES:
        return f"File exceeds maximum size ({MAX_UPLOAD_BYTES // (1024 * 1024)} MiB)."
    name = getattr(file_obj, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext and ext not in ALLOWED_EXTENSIONS:
        return f"File type '.{ext}' is not allowed."
    return None


def upload_certificate_file(file_obj):
    """Upload to S3 under Certificate/ and return the object key."""
    err = validate_upload_file(file_obj)
    if err:
        raise ValueError(err)
    ext = ""
    name = getattr(file_obj, "name", "") or ""
    if "." in name:
        ext = "." + name.rsplit(".", 1)[-1].lower()
    prefix = certificate_s3_prefix()
    key = f"{prefix}/{uuid.uuid4().hex}{ext}"

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    if not bucket:
        raise ValueError("AWS_STORAGE_BUCKET_NAME is not set")

    client = get_s3_client()
    extra = {}
    ctype = getattr(file_obj, "content_type", None)
    if ctype:
        extra["ContentType"] = ctype
    client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra)
    return key


def certificate_file_url(s3_key):
    return get_presigned_url(s3_key)
