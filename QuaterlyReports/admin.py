from django.contrib import admin
from .models import Quaters, UsersEntries, FunctionsEntries


@admin.register(Quaters)
class QuatersAdmin(admin.ModelAdmin):
    list_display = ("quater", "start_month", "end_month")


@admin.register(UsersEntries)
class UsersEntriesAdmin(admin.ModelAdmin):
    list_display = ("user", "month_and_quater_id", "date", "status")


@admin.register(FunctionsEntries)
class FunctionsEntriesAdmin(admin.ModelAdmin):
    list_display = ("Creator", "date", "status")
