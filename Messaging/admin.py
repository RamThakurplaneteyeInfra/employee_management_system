from django.contrib import admin
from .models import GroupChats, GroupMembers, IndividualChats, GroupMessages, IndividualMessages


@admin.register(GroupChats)
class GroupChatsAdmin(admin.ModelAdmin):
    list_display = ("group_id", "group_name", "created_by", "participants", "created_at")


@admin.register(GroupMembers)
class GroupMembersAdmin(admin.ModelAdmin):
    list_display = ("groupchat", "participant", "seen")


@admin.register(IndividualChats)
class IndividualChatsAdmin(admin.ModelAdmin):
    list_display = ("chat_id", "participant1", "participant2", "created_at")


@admin.register(GroupMessages)
class GroupMessagesAdmin(admin.ModelAdmin):
    list_display = ("group", "sender", "content", "created_at")


@admin.register(IndividualMessages)
class IndividualMessagesAdmin(admin.ModelAdmin):
    list_display = ("chat", "sender", "content", "seen", "created_at")
