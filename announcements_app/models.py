from django.db import models
from django.contrib.auth.models import User


class AnnouncementPost(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    announcement_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_announcement_posts",
        db_column="created_by_id",
        to_field="username",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title or "(no title)"

