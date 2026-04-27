from django.contrib import admin

from .models import AssetRequest
from .permissions import get_role_name


@admin.register(AssetRequest)
class AssetRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
        "asset_type",
        "provider",
        "department",
        "assigned_to",
        "admin_approval",
        "md_approval",
        "status",
        "created_by",
        "created_at",
    )
    list_filter = ("category", "status", "admin_approval", "md_approval", "department")
    search_fields = ("name", "asset_type", "provider", "description", "created_by__username")
    ordering = ("-created_at",)

    def has_delete_permission(self, request, obj=None):
        # Non-destructive: do not allow deleting requests from admin.
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        role_name = get_role_name(request.user)
        if role_name == "TeamLead":
            return qs.filter(created_by=request.user)
        return qs

    def get_readonly_fields(self, request, obj=None):
        role_name = get_role_name(request.user)
        readonly = {"created_at", "updated_at", "created_by"}

        if role_name == "TeamLead":
            readonly |= {"admin_approval", "md_approval", "status", "assigned_to"}
        elif role_name == "Hr":
            readonly |= {"admin_approval", "md_approval"}
        elif role_name == "MD":
            readonly |= {"admin_approval", "assigned_to", "status"}

        return tuple(sorted(readonly))

