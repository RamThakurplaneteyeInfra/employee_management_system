from django.conf import settings
from django.db import models


class AssetRequest(models.Model):
    class Category(models.TextChoices):
        HARDWARE = "Hardware", "Hardware"
        SOFTWARE = "Software", "Software"

    class ApprovalStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"

    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"
        EXPIRED = "Expired", "Expired"
        AVAILABLE = "Available", "Available"

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices)
    asset_type = models.CharField(max_length=100)
    provider = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_requests_assigned",
    )
    department = models.ForeignKey(
        "accounts.Departments",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_requests",
    )

    admin_approval = models.CharField(
        max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    md_approval = models.CharField(
        max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AVAILABLE)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_requests_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.category})"

