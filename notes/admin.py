from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "content_preview", "created_by", "created_at", "is_deleted")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("title", "content")

    readonly_fields = ("created_by", "created_at", "updated_at", "deleted_at", "deleted_by")

    def content_preview(self, obj: Note):
        content = (obj.content or "").strip()
        if len(content) > 50:
            return content[:50] + "..."
        return content

    content_preview.short_description = "Content"

    # Block hard deletion in Django admin UI.
    def has_delete_permission(self, request, obj=None):
        return False

