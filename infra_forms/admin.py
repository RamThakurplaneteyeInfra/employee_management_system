from django.contrib import admin

from .models import (
    BoqStructureEntry,
    InfraServiceType,
    LidarStructureEntry,
    ProjectCatalog,
    RouteCorridorGroup,
    SarStructureEntry,
    StructureEntry,
    StructureEntryServiceState,
)


@admin.register(RouteCorridorGroup)
class RouteCorridorGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "module", "route_label", "route_key", "created_at")
    list_filter = ("module",)
    search_fields = ("route_label", "route_key")


@admin.register(ProjectCatalog)
class ProjectCatalogAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(InfraServiceType)
class InfraServiceTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "label", "sort_order", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("code", "label")
    ordering = ("sort_order", "code")


class StructureEntryServiceStateInline(admin.TabularInline):
    model = StructureEntryServiceState
    extra = 0
    raw_id_fields = ("service_type",)


@admin.register(StructureEntry)
class StructureEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "route_group",
        "team_lead_name",
        "chainage",
        "boq_status",
        "lidar_status",
        "sar_status",
        "has_boq",
        "has_lidar",
        "has_sar",
        "date_of_entry",
        "created_at",
    )
    list_filter = (
        "has_boq",
        "has_lidar",
        "has_sar",
        "boq_status",
        "lidar_status",
        "sar_status",
        "branch",
        "date_of_entry",
    )
    search_fields = ("team_lead_name", "chainage", "structure_type", "route_corridor")
    inlines = (StructureEntryServiceStateInline,)


@admin.register(StructureEntryServiceState)
class StructureEntryServiceStateAdmin(admin.ModelAdmin):
    list_display = ("id", "structure_entry", "service_type", "inspection_status", "updated_at")
    list_filter = ("service_type", "inspection_status")
    raw_id_fields = ("structure_entry",)
    search_fields = ("remark", "structure_entry__chainage")


class _LegacyEntryAdmin(admin.ModelAdmin):
    """Legacy per-module tables (read-only, kept for backup access)."""

    list_display = (
        "id",
        "route_group",
        "team_lead_name",
        "chainage",
        "inspection_status",
        "date_of_entry",
        "created_at",
    )
    list_filter = ("inspection_status", "branch", "date_of_entry")
    search_fields = ("team_lead_name", "chainage", "structure_type", "route_corridor")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BoqStructureEntry)
class BoqStructureEntryAdmin(_LegacyEntryAdmin):
    pass


@admin.register(LidarStructureEntry)
class LidarStructureEntryAdmin(_LegacyEntryAdmin):
    pass


@admin.register(SarStructureEntry)
class SarStructureEntryAdmin(_LegacyEntryAdmin):
    pass
