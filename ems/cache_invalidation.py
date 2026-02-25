"""
Connect post_save signals to invalidate GET cache when data is created/updated.
Call connect_cache_invalidation() from an AppConfig.ready() (e.g. accounts).
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .cache_utils import invalidate_get_cache_for_prefix

# Path prefixes to invalidate per app (request.path starts with these)
PREFIXES_BY_APP = {
    "events": ["eventsapi"],
    "Messaging": ["messaging"],
    "task_management": ["tasks"],
    "notifications": ["notifications"],
    "adminpanel": ["adminapi"],
    "accounts": ["accounts"],
    "QuaterlyReports": ["getMonthlySchedule", "getUserEntries", "get_functions", "ActionableEntries"],
}


def _invalidate_for_sender(sender, **kwargs):
    app = sender._meta.app_label
    prefixes = PREFIXES_BY_APP.get(app, [])
    for prefix in prefixes:
        invalidate_get_cache_for_prefix(prefix)


def connect_cache_invalidation():
    """Call once at startup (e.g. from accounts.apps.ready()). Connects post_save to invalidate cache."""
    from events.models import BookSlot, Tour, Holiday, Event, Meeting, Room, BookingStatus, SlotMembers, tourmembers
    from Messaging.models import GroupChats, GroupMembers, IndividualChats, GroupMessages, IndividualMessages
    from task_management.models import Task, TaskAssignies, TaskMessage, TaskTypes, TaskStatus
    from notifications.models import Notification, notification_type
    from adminpanel.models import Asset, Bill, ExpenseTracker, Vendor, AssetType, BillCategory
    from accounts.models import Profile
    from QuaterlyReports.models import (
        Quaters,
        Monthly_department_head_and_subhead,
        GRPS,
        UsersEntries,
        FunctionsGoals,
        ActionableGoals,
        FunctionsEntries,
        PlannedActions,
        SalesStatistics,
    )

    models_to_watch = [
        BookSlot, Tour, Holiday, Event, Meeting, Room, BookingStatus, SlotMembers, tourmembers,
        GroupChats, GroupMembers, IndividualChats, GroupMessages, IndividualMessages,
        Task, TaskAssignies, TaskMessage, TaskTypes, TaskStatus,
        Notification, notification_type,
        Asset, Bill, ExpenseTracker, Vendor, AssetType, BillCategory,
        Profile,
        Quaters,
        Monthly_department_head_and_subhead,
        GRPS,
        UsersEntries,
        FunctionsGoals,
        ActionableGoals,
        FunctionsEntries,
        PlannedActions,
        SalesStatistics,
    ]
    for model in models_to_watch:
        post_save.connect(_invalidate_for_sender, sender=model)
