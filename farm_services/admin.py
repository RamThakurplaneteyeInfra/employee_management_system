from django.contrib import admin

from .models import FarmServiceRequest, FarmServiceSubtask, FarmServiceTask


class FarmServiceTaskInline(admin.TabularInline):
    model = FarmServiceTask
    extra = 0
    filter_horizontal = ("team_members",)


@admin.register(FarmServiceRequest)
class FarmServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "service_name", "created_by", "created_at", "updated_at")
    search_fields = ("service_name", "created_by__username")
    list_filter = ("created_at",)
    inlines = (FarmServiceTaskInline,)


@admin.register(FarmServiceTask)
class FarmServiceTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "task_name", "status", "created_at", "updated_at")
    search_fields = ("task_name", "request__service_name")
    list_filter = ("status", "created_at")
    filter_horizontal = ("team_members",)


@admin.register(FarmServiceSubtask)
class FarmServiceSubtaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "task",
        "subtask_name",
        "assigned_member",
        "created_by",
        "status",
        "created_at",
        "updated_at",
    )
    search_fields = ("subtask_name", "task__task_name", "task__request__service_name")
    list_filter = ("status", "created_at")

