from django.db import models
from django.contrib.auth.models import User


class LegacyProjectPhase(models.Model):
    """Unmanaged stub for old project.\"ProjectPhase\" table — keeps existing rows safe."""

    class Meta:
        managed = False
        db_table = 'project"."ProjectPhase'


class DeadlineProject(models.Model):
    STATUS_CHOICES = (
        ("PLANNING", "Planning"),
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("ON_HOLD", "On Hold"),
    )

    title = models.CharField(max_length=255)
    branch = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PLANNING")
    deadline = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_deadline_projects",
    )

    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project"."DeadlineProject'
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class DeadlineProjectPhase(models.Model):
    PHASE_STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
    )

    project = models.ForeignKey(
        DeadlineProject, on_delete=models.CASCADE, related_name="phases",
    )
    title = models.CharField(max_length=255)
    date = models.DateField(null=True, blank=True)
    phase_status = models.CharField(max_length=20, choices=PHASE_STATUS_CHOICES, default="PENDING")

    team_lead_id = models.IntegerField(null=True, blank=True)
    member_ids = models.JSONField(default=list, blank=True)

    checklist = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, default="")

    archived = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project"."DeadlineProjectPhase'
        ordering = ["sort_order", "created_at"]
