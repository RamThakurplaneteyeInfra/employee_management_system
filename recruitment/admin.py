from django.contrib import admin

from .models import JobApplication, JobOpening


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "department",
        "team",
        "md_status",
        "hr_status",
        "deleted_at",
        "created_by",
        "created_at",
    )
    list_filter = ("md_status", "hr_status", "department", "deleted_at")
    search_fields = ("title", "team", "department")
    raw_id_fields = ("created_by",)


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "requirement", "applied_by", "applied_at")
    list_filter = ("applied_at",)
    search_fields = ("full_name",)
    raw_id_fields = ("requirement", "applied_by")
