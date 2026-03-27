from django.contrib import admin

from .models import DeadlineProject, DeadlineProjectPhase


@admin.register(DeadlineProject)
class DeadlineProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "deadline", "created_by", "archived", "created_at")
    list_filter = ("status", "archived", "created_at")
    search_fields = ("title", "branch", "description")
    ordering = ("-created_at",)


@admin.register(DeadlineProjectPhase)
class DeadlineProjectPhaseAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "title", "phase_status", "date", "team_lead_id", "archived", "created_at")
    list_filter = ("phase_status", "archived", "created_at")
    search_fields = ("title", "notes", "project__title")
    ordering = ("project", "sort_order", "created_at")
