from django.contrib import admin

from .models import TourAdvanceAttachment, TourAdvanceMember, TourAdvanceRequest


class TourAdvanceMemberInline(admin.TabularInline):
    model = TourAdvanceMember
    extra = 0
    raw_id_fields = ("member",)


class TourAdvanceAttachmentInline(admin.TabularInline):
    model = TourAdvanceAttachment
    extra = 0
    readonly_fields = (
        "s3_key",
        "file_name",
        "file_type",
        "file_size",
        "amount",
        "created_at",
    )


@admin.register(TourAdvanceRequest)
class TourAdvanceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tour_type",
        "primary_employee",
        "created_by",
        "status",
        "advance",
        "start_date",
        "end_date",
        "created_at",
    )
    list_filter = ("status", "tour_type", "created_at")
    search_fields = (
        "primary_employee__username",
        "created_by__username",
        "client_name",
        "project",
    )
    raw_id_fields = ("primary_employee", "created_by")
    inlines = [TourAdvanceMemberInline, TourAdvanceAttachmentInline]
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff
