from django.contrib import admin
from .models import CurrentClientStage, ClientProfile, ClientProfileMembers, ClientConversation


@admin.register(CurrentClientStage)
class CurrentClientStageAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "company_name", "client_name", "status", "product_value", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["company_name", "client_name", "client_contact"]
    filter_horizontal = ["members"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ClientProfileMembers)
class ClientProfileMembersAdmin(admin.ModelAdmin):
    list_display = ["client_profile", "user"]
    list_filter = ["client_profile"]


@admin.register(ClientConversation)
class ClientConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "client", "note_preview", "created_at", "created_by"]
    list_filter = ["created_at"]
    search_fields = ["note"]

    def note_preview(self, obj):
        return obj.note[:80] + "..." if len(obj.note) > 80 else obj.note

    note_preview.short_description = "Note"
