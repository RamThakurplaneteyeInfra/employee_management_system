from django.contrib import admin
from .models import Quaters, UsersEntries, FunctionsEntries, SalesStatistics


@admin.register(Quaters)
class QuatersAdmin(admin.ModelAdmin):
    list_display = ("quater", "start_month", "end_month")


@admin.register(UsersEntries)
class UsersEntriesAdmin(admin.ModelAdmin):
    list_display = ("user", "month_and_quater_id", "date", "status", "product")


@admin.register(FunctionsEntries)
class FunctionsEntriesAdmin(admin.ModelAdmin):
    list_display = ("id", "Creator", "product", "date", "final_Status")


@admin.register(SalesStatistics)
class SalesStatisticsAdmin(admin.ModelAdmin):
    list_display = ("id", "grp", "product", "status")
