from django.contrib import admin

from .models import AnnouncementPost


@admin.register(AnnouncementPost)
class AnnouncementPostAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "announcement_date", "created_at", "created_by")
    search_fields = ("title", "description", "created_by__username")
    list_filter = ("announcement_date", "created_at")

