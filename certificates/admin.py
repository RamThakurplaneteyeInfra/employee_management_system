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
