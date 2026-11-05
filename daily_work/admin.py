from django.contrib import admin

from .models import DailyProject, DailyWorkReport, DailyWorkReportSeen, ProjectAssignment


class ProjectAssignmentInline(admin.TabularInline):
    model = ProjectAssignment
    extra = 0
    raw_id_fields = ("user",)


@admin.register(DailyProject)
class DailyProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "project_name", "team_lead", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("project_name", "team_lead__username")
    inlines = [ProjectAssignmentInline]


@admin.register(DailyWorkReport)
class DailyWorkReportAdmin(admin.ModelAdmin):
    list_display = ("id", "report_date", "employee", "project", "status")
    list_filter = ("status", "report_date")
    search_fields = ("employee_name", "employee__username", "project__project_name")
    raw_id_fields = ("employee", "project")


@admin.register(DailyWorkReportSeen)
class DailyWorkReportSeenAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "viewer", "seen_at")
    search_fields = ("viewer__username", "report__employee_name")
    raw_id_fields = ("report", "viewer")
