from __future__ import annotations

from django.conf import settings
from django.db import models


class AiSummary(models.Model):
    class SummaryType(models.TextChoices):
        INTERN = "intern", "intern"
        EMPLOYEE = "employee", "employee"
        TEAMLEAD = "teamlead", "teamlead"
        MD = "md", "md"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_summaries",
        help_text="Nullable for org-wide summaries (type=md).",
    )
    type = models.CharField(max_length=20, choices=SummaryType.choices, db_index=True)
    metrics = models.JSONField(default=dict)
    markdown = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["type", "-created_at"]),
            models.Index(fields=["user", "type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"AiSummary(type={self.type}, user={getattr(self.user, 'username', None)}, created_at={self.created_at})"

