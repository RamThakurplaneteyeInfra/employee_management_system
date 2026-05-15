from django.contrib import admin

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_name", "asset_type", "assigned_to", "start_at", "end_at")
    list_filter = ("asset_type",)
    search_fields = ("asset_name", "assigned_to", "location", "purpose")
