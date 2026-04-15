from django.conf import settings
from django.db import models


class ApprovalStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"


class JobState(models.TextChoices):
    OPEN = "Open", "Open"
    CLOSED = "Closed", "Closed"


class JobOpening(models.Model):
    """Job requisition. Public list/detail only exposes rows that are fully approved."""

    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    team = models.CharField(max_length=100)
    employment_type = models.CharField(
        max_length=50,
        help_text="e.g. Full-time, Part-time, Contract",
    )
    num_positions = models.PositiveIntegerField(default=1)
    required_experience = models.CharField(max_length=100, blank=True)
    primary_skills = models.CharField(max_length=500, blank=True)
    education = models.CharField(max_length=100, blank=True)
    tools_tech = models.CharField(max_length=500, blank=True)
    md_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    hr_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    job_state = models.CharField(
        max_length=10,
        choices=JobState.choices,
        default=JobState.OPEN,
        help_text="Operational state controlled by Team Leads: Open/Closed.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_openings_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Soft-delete: set by DELETE /api/jobs/{id}/; row is not removed from DB.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.department})"


class JobApplication(models.Model):
    """Candidate application for a job opening."""

    requirement = models.ForeignKey(
        JobOpening,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    full_name = models.CharField(max_length=200, blank=True, default="")
    resume = models.FileField(upload_to="job_resumes/")
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_applications_submitted",
    )
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-applied_at"]

    def __str__(self):
        return f"{self.full_name} → {self.requirement_id}"
