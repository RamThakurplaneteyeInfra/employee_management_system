from django.contrib import admin
from .models import Call,GroupCall,GroupCallParticipant

@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "receiver", "call_type", "status", "timestamp")
    list_filter = ("call_type", "status")
    search_fields = ("sender__username", "receiver__username")
    readonly_fields = ("timestamp",)


@admin.register(GroupCall)
class GroupCallAdmin(admin.ModelAdmin):
    list_display = ("id", "creator", "call_type", "status", "created_at")
    list_filter = ("call_type", "status")
    search_fields = ("creator__username",)
    readonly_fields = ("created_at",)


@admin.register(GroupCallParticipant)
class GroupCallParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "group_call", "user", "status", "joined_at")
    list_filter = ("status",)
    search_fields = ("user__username",)

# Register your models here.
