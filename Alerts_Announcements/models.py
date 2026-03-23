"""
Alerts & Announcements app: Alert (alerts schema), Announcement (project schema).
"""
from django.db import models
from accounts.models import User
from task_management.models import TaskStatus
from project.models import Product


# =============================================================================
# Schema: alerts
# =============================================================================

class AlertType(models.Model):
    """Type/category of an alert (e.g. System, Security, Info)."""
    type_name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'alerts"."alert_types'
        verbose_name = "Alert type"
        verbose_name_plural = "Alert types"
        ordering = ["type_name"]

    def __str__(self):
        return self.type_name


class Alert(models.Model):
    """Alert: title, type, severity, creator, details, timestamps, closure, status."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SEVERITY_CHOICES = [
        (HIGH, "High"),
        (MEDIUM, "Medium"),
        (LOW, "Low"),
    ]

    alert_title = models.TextField()
    alert_type = models.ForeignKey(
        AlertType,
        on_delete=models.CASCADE,
        related_name="alerts",
        db_column="alert_type_id",
    )
    alert_severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
    )
    alert_creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_alerts",
        db_column="alert_creator_id",
        to_field="username",
    )
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    close_at = models.DateTimeField(null=True, blank=True)  # Set when alert is closed
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="closed_alerts",
        db_column="closed_by_id",
        to_field="username",
    )
    closed_by=models.DateTimeField(auto_now=False,auto_now_add=False,null=False)
    status = models.ForeignKey(
        TaskStatus,
        on_delete=models.CASCADE,
        related_name="alerts",
        db_column="status_id",
        default=1,  # PENDING in task_statuses
    )

    class Meta:
        db_table = 'alerts"."Alerts'
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"
        ordering = ["-created_at"]

    def __str__(self):
        return self.alert_title[:50] or "(no title)"


# =============================================================================
# Schema: project (AnnouncementType and Announcement live in project schema)
# =============================================================================

class AnnouncementType(models.Model):
    """Type of announcement (e.g. Product, General, Campaign)."""
    type_name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'project"."announcement_types'
        verbose_name = "Announcement type"
        verbose_name_plural = "Announcement types"
        ordering = ["type_name"]

    def __str__(self):
        return self.type_name


class Announcement(models.Model):
    """Announcement: text, creator, type, product, percentage, etc."""
    announcement = models.TextField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_announcements",
        db_column="created_by_id",
        to_field="username",
    )
    type = models.ForeignKey(
        AnnouncementType,
        on_delete=models.CASCADE,
        related_name="announcements",
        db_column="type_id",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="announcements",
        db_column="product_id",
    )
    percentage = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project"."Announcements'
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
        ordering = ["-created_at"]

    def __str__(self):
        return (self.announcement[:50] + "…") if len(self.announcement) > 50 else self.announcement


# =============================================================================
# Schema: attention (separate from Alert/“alter”)
# =============================================================================
class Attention(models.Model):
    """Attention: separate section from Alert (“alter”) with role-based visibility."""

    STATUS_PENDING = 1
    STATUS_IN_PROGRESS = 2
    STATUS_COMPLETE = 3
    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_IN_PROGRESS, "in_progress"),
        (STATUS_COMPLETE, "complete"),
    ]

    attention_title = models.TextField()
    description = models.TextField()
    # 1=pending, 2=in_progress, 3=complete
    # Non-null + default ensures existing rows backfill automatically during migration.
    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_PENDING, null=False, blank=False)
    attention_creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_attentions",
        db_column="attention_creator_id",
        to_field="username",
    )
    # Employee selected from frontend dropdown; used for HR/Admin visibility scoping.
    # Nullable for backward compatibility with any existing Attention rows created
    # before this field existed.
    target_employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="targeted_attentions",
        db_column="target_employee_id",
        to_field="username",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'alerts"."Attention'
        ordering = ["-created_at"]

    def __str__(self):
        return self.attention_title[:50] or "(no title)"
