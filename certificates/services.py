"""Shared certificate create helpers (single + batch)."""
from .models import EmployeeCertificate
from .s3_helpers import upload_certificate_file

BATCH_MAX_FILES = 20


def normalize_batch_field_list(data, *keys):
    """Return parallel list from multipart getlist or single value."""
    for key in keys:
        if hasattr(data, "getlist"):
            values = data.getlist(key)
            if values:
                return values
        else:
            raw = data.get(key)
            if raw is None:
                continue
            if isinstance(raw, list):
                return raw
            return [raw]
    return []


def _pad_metadata_list(values, count, max_len):
    if not values:
        return [""] * count
    cleaned = [str(v).strip()[:max_len] for v in values]
    if len(cleaned) == 1 and count > 1:
        return cleaned * count
    if len(cleaned) != count:
        return None
    return cleaned


def parse_batch_items(request):
    """
    Parse multipart batch fields. Returns (employee_id, items).
    items: list of dicts {file, title, description}
    """
    files = request.FILES.getlist("file")
    if not files:
        single = request.FILES.get("file")
        if single:
            files = [single]
    if not files:
        raise ValueError("Send at least one file (repeat field name 'file' per certificate).")
    if len(files) > BATCH_MAX_FILES:
        raise ValueError(f"Maximum {BATCH_MAX_FILES} files per request.")

    titles = _pad_metadata_list(
        normalize_batch_field_list(request.data, "title"), len(files), 200
    )
    if titles is None:
        raise ValueError(
            f"title count must be 0, 1, or match file count ({len(files)})."
        )
    descriptions = _pad_metadata_list(
        normalize_batch_field_list(request.data, "description"), len(files), 500
    )
    if descriptions is None:
        raise ValueError(
            f"description count must be 0, 1, or match file count ({len(files)})."
        )

    employee_id = (request.data.get("employeeId") or "").strip()
    items = [
        {"file": f, "title": titles[i], "description": descriptions[i]}
        for i, f in enumerate(files)
    ]
    return employee_id, items


def create_certificate_record(owner, uploaded_by, file_obj, title="", description=""):
    """Upload to S3 and return unsaved EmployeeCertificate instance."""
    s3_key = upload_certificate_file(file_obj)
    return EmployeeCertificate(
        employee=owner,
        uploaded_by=uploaded_by,
        title=title or "",
        description=description or "",
        s3_key=s3_key,
        file_name=getattr(file_obj, "name", "") or "",
        file_type=getattr(file_obj, "content_type", "") or "",
        file_size=int(getattr(file_obj, "size", 0) or 0),
    )


def create_certificates_batch(owner, uploaded_by, items):
    """Validate all files, upload each, bulk_insert rows."""
    from .s3_helpers import validate_upload_file

    for i, item in enumerate(items):
        err = validate_upload_file(item["file"])
        if err:
            raise ValueError(f"File {i + 1}: {err}")

    records = [
        create_certificate_record(
            owner,
            uploaded_by,
            item["file"],
            title=item.get("title", ""),
            description=item.get("description", ""),
        )
        for item in items
    ]
    return EmployeeCertificate.objects.bulk_create(records)
