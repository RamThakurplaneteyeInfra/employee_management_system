from django.contrib import admin

from .models import EmployeeCertificate


@admin.register(EmployeeCertificate)
class EmployeeCertificateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee",
        "title",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("employee__username", "title", "description", "file_name")
    readonly_fields = ("created_at", "updated_at", "s3_key")

    def delete_model(self, request, obj):
        obj.is_active = False
        obj.save(update_fields=["is_active", "updated_at"])

    def delete_queryset(self, request, queryset):
        queryset.update(is_active=False)
