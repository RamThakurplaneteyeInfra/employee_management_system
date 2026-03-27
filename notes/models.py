from django.conf import settings
from django.db import models
from django.utils import timezone


class Note(models.Model):
    """
    Personal notes: each note belongs to exactly one user (created_by).
    We use soft-delete so the DELETE endpoint never removes rows from DB.
    """

    title = models.CharField(max_length=200, blank=True, null=True)
    content = models.TextField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notes_created",
        db_column="created_by_id",
    )

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notes_deleted",
        db_column="deleted_by_id",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Keep it in an existing schema so it doesn't break your DB search_path.
        db_table = 'team_management"."UserNotes'
        verbose_name = "note"
        verbose_name_plural = "notes"
        ordering = ["-created_at"]

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user is not None and getattr(user, "is_authenticated", False):
            self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    def __str__(self):
        preview = (self.content or "").strip()
        if len(preview) > 25:
            preview = preview[:25] + "..."
        return self.title or preview or f"Note {self.pk}"

