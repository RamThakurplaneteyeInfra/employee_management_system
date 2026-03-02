"""
Shared AWS S3 helpers: upload to a prefix and generate presigned URLs.
- Employee_Photo/ : profile photos (via DEFAULT_FILE_STORAGE in settings).
- files/          : all other uploads (messaging, etc.) via upload_file_to_files().
"""
from django.conf import settings


def get_s3_client():
    """Lazy boto3 S3 client. Raises ValueError if bucket not configured."""
    import boto3
    if not getattr(settings, "AWS_STORAGE_BUCKET_NAME", None):
        raise ValueError("AWS_STORAGE_BUCKET_NAME is not set")
    return boto3.client(
        "s3",
        region_name=getattr(settings, "AWS_S3_REGION_NAME", "ap-south-1"),
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY"),
    )


def get_presigned_url(s3_key, expires=None):
    """
    Return a presigned GET URL for the object.

    :param s3_key: S3 object key (path).
    :param expires: URL expiry in seconds (default: AWS_S3_PRESIGNED_EXPIRY).
    :return: str Presigned URL, or None if key is empty or client fails.
    """
    if not s3_key:
        return None
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    if not bucket:
        return None
    expiry = expires if expires is not None else getattr(settings, "AWS_S3_PRESIGNED_EXPIRY", 3600)
    try:
        client = get_s3_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=expiry,
        )
    except Exception:
        return None


def upload_file_to_files(file_obj, sub_prefix=None):
    """
    Upload a file to S3 under the files/ prefix (for all non–employee-photo uploads).

    :param file_obj: Django UploadedFile (e.g. request.FILES['file'])
    :param sub_prefix: Optional subfolder under files/ (e.g. "messaging")
    :return: str S3 key of the uploaded file.
    """
    import uuid
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    base = (getattr(settings, "AWS_S3_FILES_PREFIX", "files/") or "files/").strip("/")
    if sub_prefix:
        base = f"{base}/{sub_prefix.strip('/')}"
    ext = ""
    if hasattr(file_obj, "name") and "." in file_obj.name:
        ext = "." + file_obj.name.rsplit(".", 1)[-1].lower()
    key = f"{base}/{uuid.uuid4().hex}{ext}"
    client = get_s3_client()
    extra = {}
    if hasattr(file_obj, "content_type") and file_obj.content_type:
        extra["ContentType"] = file_obj.content_type
    client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra)
    return key


def delete_file_from_files(s3_key):
    """
    Delete an object from S3 (files/ prefix). No-op if key is empty or delete fails.

    :param s3_key: S3 object key (path) returned by upload_file_to_files.
    :return: True if deleted or key empty, False on error.
    """
    if not s3_key:
        return True
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    if not bucket:
        return False
    try:
        client = get_s3_client()
        client.delete_object(Bucket=bucket, Key=s3_key)
        return True
    except Exception:
        return False
