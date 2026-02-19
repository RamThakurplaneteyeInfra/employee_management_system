from django.contrib import admin
from .models import notification_type, Notification


@admin.register(notification_type)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "type_name")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "type_of_notification", "from_user", "receipient", "is_read", "created_at")
    list_filter = ("type_of_notification", "is_read")
    search_fields = ("message", "from_user__username", "receipient__username")
