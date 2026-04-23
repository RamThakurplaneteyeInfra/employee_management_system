from django.contrib import admin

from .models import BoqStructureEntry, LidarStructureEntry, ProjectCatalog, RouteCorridorGroup, SarStructureEntry


@admin.register(RouteCorridorGroup)
class RouteCorridorGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "module", "route_label", "route_key", "created_at")
    list_filter = ("module",)
    search_fields = ("route_label", "route_key")


@admin.register(ProjectCatalog)
class ProjectCatalogAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


class _EntryAdmin(admin.ModelAdmin):
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


@admin.register(BoqStructureEntry)
class BoqStructureEntryAdmin(_EntryAdmin):
    pass


@admin.register(LidarStructureEntry)
class LidarStructureEntryAdmin(_EntryAdmin):
    pass


@admin.register(SarStructureEntry)
class SarStructureEntryAdmin(_EntryAdmin):
    pass
