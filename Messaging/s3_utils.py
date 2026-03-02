"""
Upload and retrieve messaging files from AWS S3 under the files/ prefix.
Uses shared ems.s3_utils for client and presigned URLs.
"""
from django.conf import settings

from ems.s3_utils import get_presigned_url, upload_file_to_files


def upload_file(file_obj, prefix=None):
    """
    Upload a file to S3 under the files/ prefix (subfolder optional, e.g. "messaging").

    :param file_obj: Django UploadedFile (request.FILES['file'])
    :param prefix: Optional subfolder under files/ (e.g. "messaging")
    :return: str S3 key (path) of the uploaded file.
    """
    return upload_file_to_files(file_obj, sub_prefix=prefix or "messaging")


def get_file_url(s3_key, expires=None):
    """Return a presigned GET URL for the object. See ems.s3_utils.get_presigned_url."""
    return get_presigned_url(s3_key, expires=expires)
