from django.conf import settings
from django.db import models


class FarmServiceRequest(models.Model):
    service_name = models.CharField(max_length=160)
    puc = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="farm_service_requests_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["created_by"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"FarmServiceRequest #{self.pk} ({self.service_name})"


class FarmServiceTask(models.Model):
    request = models.ForeignKey(
        FarmServiceRequest,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    task_name = models.CharField(max_length=200)
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="farm_service_tasks_assigned",
        blank=True,
    )
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["request"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"FarmServiceTask #{self.pk} ({self.task_name})"


class FarmServiceSubtask(models.Model):
    task = models.ForeignKey(
        FarmServiceTask,
        on_delete=models.CASCADE,
        related_name="subtasks",
    )
    subtask_name = models.CharField(max_length=220)
    assigned_member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="farm_service_subtasks_assigned",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="farm_service_subtasks_created",
    )
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"FarmServiceSubtask #{self.pk} ({self.subtask_name})"

