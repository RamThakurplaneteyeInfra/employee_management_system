from django.contrib import admin

from .models import CustomerPanelAmountLog, CustomerPanelEntry


@admin.register(CustomerPanelEntry)
class CustomerPanelEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business_name",
        "serial_no",
        "product",
        "service",
        "value",
        "tax_percent",
        "total",
        "created_by",
        "created_at",
    )
    search_fields = ("business_name", "serial_no", "representative_name", "product", "service")
    ordering = ("-created_at",)


@admin.register(CustomerPanelAmountLog)
class CustomerPanelAmountLogAdmin(admin.ModelAdmin):
    list_display = ("id", "entry", "amount", "date", "notes", "created_at")
    search_fields = ("entry__business_name", "notes")
    ordering = ("-date", "-created_at")

