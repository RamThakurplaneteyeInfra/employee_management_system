"""
Connect post_save and post_delete signals to invalidate GET cache when data changes.
Uses model-specific path prefixes so only affected GET endpoints are invalidated
(e.g. Task create invalidates viewTasks + viewAssignedTasks + Taskcount, not all /tasks/).
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .cache_utils import invalidate_get_cache_for_prefix

# Fallback: path prefixes to invalidate per app when a model has no specific mapping
PREFIXES_BY_APP = {
    "events": ["eventsapi"],
    "Messaging": ["messaging"],
    "task_management": ["tasks"],
    "notifications": ["notifications"],
    "adminpanel": ["adminapi"],
    "accounts": ["accounts"],
    "QuaterlyReports": ["getMonthlySchedule", "getUserEntries", "get_functions", "ActionableEntries"],
}

# Model-specific GET path prefixes (path_safe format: colons, e.g. "tasks:viewTasks").
# Only these endpoints are invalidated when this model is saved/deleted.
AFFECTED_GET_PREFIXES_BY_MODEL = {
    # task_management: task list and assignment views + task count
    "task_management.Task": [
        "tasks:viewTasks",
        "tasks:viewAssignedTasks",
        "tasks:Taskcount",
    ],
    "task_management.TaskAssignies": [
        "tasks:viewTasks",
        "tasks:viewAssignedTasks",
        "tasks:Taskcount",
    ],
    "task_management.TaskMessage": [
        "tasks:getMessage",
    ],
    "task_management.TaskTypes": [
        "tasks:getTaskTypes",
    ],
    "task_management.TaskStatus": [
        "tasks:getTaskStatuses",
    ],
    # accounts: employee list, dashboard, and birthday counter (under eventsapi)
    "accounts.Profile": [
        "accounts:employees",
        "accounts:employee",
        "accounts:admin",
        "eventsapi:events:birthdaycounter",
    ],
    # notifications
    "notifications.Notification": [
        "notifications:today",
        "notifications:types",
    ],
    "notifications.notification_type": [
        "notifications:types",
    ],
    # QuaterlyReports: only endpoints that show entries/goals
    "QuaterlyReports.UsersEntries": [
        "getUserEntries",
    ],
    "QuaterlyReports.FunctionsEntries": [
        "ActionableEntries",
    ],
    # Calling (under /messaging/): call lists and callable users
    "Calling.Call": [
        "messaging:callableUsers",
        "messaging:activeCalls",
        "messaging:pendingCalls",
    ],
    "Calling.GroupCall": [
        "messaging:activeGroupCalls",
    ],
    "QuaterlyReports.Monthly_department_head_and_subhead": [
        "getMonthlySchedule",
    ],
    "QuaterlyReports.FunctionsGoals": [
        "get_functions",
    ],
    "QuaterlyReports.ActionableGoals": [
        "get_functions",
    ],
}


def _invalidate_for_sender(sender, **kwargs):
    model_key = f"{sender._meta.app_label}.{sender._meta.model_name}"
    prefixes = AFFECTED_GET_PREFIXES_BY_MODEL.get(model_key)
    if prefixes is None:
        prefixes = PREFIXES_BY_APP.get(sender._meta.app_label, [])
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
    from Calling.models import Call, GroupCall, GroupCallParticipant
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
        Call,
        GroupCall,
        GroupCallParticipant,
    ]
    for model in models_to_watch:
        post_save.connect(_invalidate_for_sender, sender=model)
        post_delete.connect(_invalidate_for_sender, sender=model)
