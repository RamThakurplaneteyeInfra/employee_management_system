"""
Team-lead project assignments and daily work reports.

Assignments point at existing auth users. Removing an assignment does not
delete that person's reports.
"""

from django.conf import settings
from django.db import models

from .categories import empty_updates


class DailyProject(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    project_name = models.CharField(max_length=255)
    project_description = models.TextField(blank=True, default="")
    team_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="daily_work_led_projects",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_work"."DailyProject'
        ordering = ["project_name", "id"]
        verbose_name = "Daily work project"

    def __str__(self):
        return self.project_name


class ProjectAssignment(models.Model):
    class MemberType(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        INTERN = "intern", "Intern"

    project = models.ForeignKey(
        DailyProject,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="daily_work_assignments",
    )
    member_type = models.CharField(max_length=10, choices=MemberType.choices)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'daily_work"."ProjectAssignment'
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                name="daily_work_one_assignment_per_user",
            ),
        ]
        verbose_name = "Project assignment"

    def __str__(self):
        return f"{self.user_id} on {self.project_id} ({self.member_type})"


class DailyWorkReport(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"

    project = models.ForeignKey(
        DailyProject,
        on_delete=models.PROTECT,
        related_name="reports",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="daily_work_reports",
    )
    report_date = models.DateField()
    employee_name = models.CharField(max_length=255, blank=True, default="")
    employee_category = models.CharField(max_length=255, blank=True, default="")
    updates = models.JSONField(default=empty_updates)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_work"."DailyWorkReport'
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "project", "report_date"],
                name="daily_work_one_report_per_day",
            ),
        ]
        ordering = ["-report_date", "-id"]
        verbose_name = "Daily work report"

    def __str__(self):
        return f"{self.employee_id} {self.report_date} project {self.project_id}"


class DailyWorkReportSeen(models.Model):
    """Tracks that a viewer has opened someone else's daily report."""

    report = models.ForeignKey(
        DailyWorkReport,
        on_delete=models.CASCADE,
        related_name="seen_by",
    )
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_work_reports_seen",
    )
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'daily_work"."DailyWorkReportSeen'
        constraints = [
            models.UniqueConstraint(
                fields=["report", "viewer"],
                name="daily_work_one_seen_per_viewer",
            ),
        ]
        verbose_name = "Daily work report seen"

    def __str__(self):
        return f"viewer {self.viewer_id} saw report {self.report_id}"
