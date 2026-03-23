from django.contrib import admin
from .models import AlertType, Alert, AnnouncementType, Announcement, Attention


@admin.register(AlertType)
class AlertTypeAdmin(admin.ModelAdmin):
    list_display = ("type_name",)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("alert_title", "alert_type", "alert_severity", "alert_creator", "status", "created_at", "close_at", "closed_by")
    list_filter = ("alert_severity", "alert_type", "status")
    search_fields = ("alert_title", "details")


@admin.register(AnnouncementType)
class AnnouncementTypeAdmin(admin.ModelAdmin):
    list_display = ("type_name",)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("announcement", "type", "created_by", "product", "percentage", "created_at")
    list_filter = ("type", "product")


@admin.register(Attention)
class AttentionAdmin(admin.ModelAdmin):
    list_display = ("attention_title", "attention_creator", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("attention_title", "description")
