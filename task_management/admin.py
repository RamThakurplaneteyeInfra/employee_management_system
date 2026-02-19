from django.contrib import admin
from .models import TaskTypes, TaskStatus, Task, TaskAssignies, TaskMessage


@admin.register(TaskTypes)
class TaskTypesAdmin(admin.ModelAdmin):
    list_display = ("type_id", "type_name")


@admin.register(TaskStatus)
class TaskStatusAdmin(admin.ModelAdmin):
    list_display = ("status_id", "status_name")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("task_id", "title", "created_by", "status", "type", "due_date", "created_at")
    list_filter = ("status", "type")
    search_fields = ("title", "description")


@admin.register(TaskAssignies)
class TaskAssigniesAdmin(admin.ModelAdmin):
    list_display = ("task", "assigned_to")


@admin.register(TaskMessage)
class TaskMessageAdmin(admin.ModelAdmin):
    list_display = ("task", "sender", "message", "created_at")
