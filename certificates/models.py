"""
Employee certificates — metadata in DB, files in S3 under Certificate/.
"""
from django.conf import settings
from django.db import models

CERTIFICATE_S3_PREFIX = "Certificate"


class EmployeeCertificate(models.Model):
    """One certificate file per row; soft-deactivate only (no hard delete)."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="employee_certificates",
        help_text="Certificate owner (creator).",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="certificates_uploaded",
    )
    title = models.CharField(max_length=200, blank=True, default="")
    description = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Short description of the certificate.",
    )
    s3_key = models.CharField(max_length=512)
    file_name = models.CharField(max_length=255, blank=True, default="")
    file_type = models.CharField(max_length=128, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="False = soft-deactivated; row and S3 object are retained.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certificates"."EmployeeCertificate'
        ordering = ["-created_at", "-id"]
        verbose_name = "Employee certificate"
        verbose_name_plural = "Employee certificates"
        indexes = [
            models.Index(fields=["employee", "is_active"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        label = self.title or self.file_name or self.s3_key
        return f"{self.employee_id}: {label}"
