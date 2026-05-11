from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from .models import (
    Profile,
    User,
    LeaveTypes,
    LeaveStatus,
    LeaveSummary,
    LeaveApplicationData,
)

admin.site.unregister(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("id","username", "email", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
# @admin.register(User,CustomUserAdmin)

admin.site.register(User,CustomUserAdmin)


@admin.register(Profile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("Role", "Name", "Designation","Employee_id")


@admin.register(LeaveTypes)
class LeaveTypesAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("id",)


@admin.register(LeaveStatus)
class LeaveStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("id",)


@admin.register(LeaveSummary)
class LeaveSummaryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "total_leaves",
        "used_leaves",
        "emergency_leaves",
        "remaining_leaves",
        "casual_leaves",
        "earn_leaves",
        "menstrual_leaves",
        "unpaid_leaves",
        "short_leaves_remaining",
        "short_leave_credit_month_first",
    )
    search_fields = ("user__username", "user__email")
    list_filter = ("total_leaves",)
    readonly_fields = ("emergency_leaves",)

    def remaining_leaves(self, obj):
        return obj.remaining_leaves
    remaining_leaves.short_description = "Remaining"


@admin.register(LeaveApplicationData)
class LeaveApplicationDataAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applicant",
        "leave_type",
        "start_date",
        "duration_of_days",
        "is_emergency",
        "team_lead_approval",
        "HR_approval",
        "MD_approval",
        "admin_approval",
        "alternative_approval",
        "application_date",
    )
    list_filter = (
        "leave_type",
        "is_emergency",
        "MD_approval",
        "HR_approval",
        "team_lead_approval",
        "admin_approval",
        "application_date",
    )
    search_fields = (
        "applicant__username",
        "applicant__email",
        "leave_subject",
        "reason",
    )
    autocomplete_fields = ("applicant", "team_lead", "alternative", "alternative_approval")
    date_hierarchy = "application_date"
    readonly_fields = ("application_date", "approved_by_MD_at")
    ordering = ("-application_date", "-id")

