"""
Tour advance requests — separate from events.Tour (team tours) and
adminpanel.ExpenseMonthlyAdvance (monthly office expense budget).
"""
from django.conf import settings
from django.db import models

# New uploads; legacy keys under TOUR_ADVANCE_S3_PREFIX_LEGACY remain valid.
TOUR_ADVANCE_S3_PREFIX = "Billing_Attachment"
TOUR_ADVANCE_S3_PREFIX_LEGACY = "Attachment/TourAdvance"


class TourAdvanceRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"

    tour_type = models.CharField(max_length=100, blank=True, default="")
    project = models.CharField(max_length=255, blank=True, default="")
    division = models.CharField(max_length=255, blank=True, default="")
    from_location = models.CharField(max_length=255, blank=True, default="")
    from_location_pincode = models.CharField(max_length=20, blank=True, default="")
    to_location = models.CharField(max_length=255, blank=True, default="")
    to_location_pincode = models.CharField(max_length=20, blank=True, default="")
    client_name = models.CharField(max_length=255, blank=True, default="")
    purpose_of_visit = models.TextField(blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    no_of_days = models.PositiveIntegerField(default=0)
    advance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    primary_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tour_advance_primary",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tour_advance_created",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="TourAdvanceMember",
        related_name="tour_advance_memberships",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tour_advance"."TourAdvanceRequest'
        ordering = ["-created_at", "-id"]
        verbose_name = "Tour advance request"

    def __str__(self):
        return f"TourAdvance #{self.pk} ({self.primary_employee_id})"


class TourAdvanceMember(models.Model):
    """Through table: employees who can view this tour advance request."""

    request = models.ForeignKey(
        TourAdvanceRequest,
        on_delete=models.CASCADE,
        related_name="member_links",
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tour_advance_member_links",
    )

    class Meta:
        db_table = 'tour_advance"."TourAdvanceMember'
        unique_together = ("request", "member")
        verbose_name = "Tour advance member"

    def __str__(self):
        return f"{self.request_id} — {self.member_id}"


class TourAdvanceAttachment(models.Model):
    request = models.ForeignKey(
        TourAdvanceRequest,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    s3_key = models.CharField(max_length=512)
    file_name = models.CharField(max_length=255, blank=True, default="")
    file_type = models.CharField(max_length=128, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tour_advance_attachments_uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tour_advance"."TourAdvanceAttachment'
        ordering = ["created_at", "id"]
        verbose_name = "Tour advance attachment"

    def __str__(self):
        return self.file_name or self.s3_key
