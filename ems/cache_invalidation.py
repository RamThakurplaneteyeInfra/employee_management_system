"""
Connect post_save and post_delete signals to invalidate GET cache when data changes.
Invalidation is per-user: only the affected user(s) cache keys are cleared (cache key includes user_id).
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .cache_utils import invalidate_get_cache_for_prefix, invalidate_get_cache_for_messaging_scope


def _get_affected_user_ids(sender, instance, **kwargs):
    """Return list of user pks whose cache should be invalidated when this model instance changes, or None if not scoped."""
    model_key = f"{sender._meta.app_label}.{sender._meta.model_name}"
    label = getattr(sender._meta, "label", None)  # e.g. QuaterlyReports.FunctionsEntries (matches dict keys)
    try:
        if model_key == "task_management.Task":
            pks = []
            if hasattr(instance, "created_by") and instance.created_by_id is not None:
                cb = instance.created_by
                pks.append(cb.pk if hasattr(cb, "pk") else None)
            for u in (getattr(instance, "assignees", None) or []).all() if hasattr(instance, "assignees") else []:
                if getattr(u, "pk", None) is not None:
                    pks.append(u.pk)
            return list(filter(None, set(pks)))
        if model_key == "task_management.TaskAssignies":
            pks = []
            if hasattr(instance, "assigned_to") and instance.assigned_to_id is not None:
                pks.append(instance.assigned_to.pk)
            if hasattr(instance, "task_id") and instance.task_id is not None:
                from task_management.models import Task
                try:
                    t = Task.objects.get(pk=instance.task_id)
                    if t.created_by_id:
                        pks.append(t.created_by.pk)
                except Exception:
                    pass
            return list(filter(None, set(pks)))
        if model_key == "task_management.TaskMessage":
            if hasattr(instance, "task_id") and instance.task_id is not None:
                from task_management.models import Task
                try:
                    t = Task.objects.get(pk=instance.task_id)
                    pks = [t.created_by.pk]
                    for u in t.assignees.all():
                        pks.append(u.pk)
                    return list(filter(None, set(pks)))
                except Exception:
                    pass
            return []
        if model_key == "accounts.Profile":
            e = getattr(instance, "Employee_id", None)
            if e is not None and getattr(e, "pk", None) is not None:
                return [e.pk]
            return []
        if model_key == "notifications.Notification":
            r = getattr(instance, "receipient", None)
            if r is not None and getattr(r, "pk", None) is not None:
                return [r.pk]
            return []
        if model_key == "QuaterlyReports.UsersEntries":
            u = getattr(instance, "user", None)
            if u is not None and getattr(u, "pk", None) is not None:
                return [u.pk]
            return []
        if model_key == "QuaterlyReports.functionsentries" or label == "QuaterlyReports.FunctionsEntries":
            pks = []
            c = getattr(instance, "Creator", None)
            if c is not None:
                pks.append(getattr(c, "pk", None))
            co = getattr(instance, "co_author", None)
            if co is not None:
                pks.append(getattr(co, "pk", None))
            # Everyone in the share chain must see fresh data (list/detail APIs)
            try:
                entry_id = getattr(instance, "pk", None) or getattr(instance, "id", None)
                if entry_id:
                    from QuaterlyReports.models import FunctionsEntriesShare
                    for row in FunctionsEntriesShare.objects.filter(actionable_entry_id=entry_id).select_related("shared_with"):
                        u = getattr(row, "shared_with", None)
                        if u is not None:
                            pks.append(getattr(u, "pk", None))
            except Exception:
                pass
            return list(filter(None, set(pks)))
        if model_key == "QuaterlyReports.functionsentriesshare" or label == "QuaterlyReports.FunctionsEntriesShare":
            # Invalidate for the shared_with user, creator, co_author, and everyone else on the share chain
            pks = []
            sw = getattr(instance, "shared_with", None)
            if sw is not None:
                pks.append(getattr(sw, "pk", None))
            entry = getattr(instance, "actionable_entry", None)
            if entry is None and getattr(instance, "actionable_entry_id", None):
                try:
                    from QuaterlyReports.models import FunctionsEntries
                    entry = FunctionsEntries.objects.filter(pk=instance.actionable_entry_id).first()
                except Exception:
                    entry = None
            if entry is not None:
                c = getattr(entry, "Creator", None)
                if c is not None:
                    pks.append(getattr(c, "pk", None))
                co = getattr(entry, "co_author", None)
                if co is not None:
                    pks.append(getattr(co, "pk", None))
                try:
                    from QuaterlyReports.models import FunctionsEntriesShare
                    for row in FunctionsEntriesShare.objects.filter(actionable_entry_id=entry.pk).select_related("shared_with"):
                        u = getattr(row, "shared_with", None)
                        if u is not None:
                            pks.append(getattr(u, "pk", None))
                except Exception:
                    pass
            return list(filter(None, set(pks)))
        if model_key == "QuaterlyReports.Monthly_department_head_and_subhead":
            return None
        if model_key == "QuaterlyReports.FunctionsGoals" or model_key == "QuaterlyReports.ActionableGoals":
            return None
        if model_key == "task_management.TaskTypes" or model_key == "task_management.TaskStatus":
            return None
        if model_key == "notifications.notification_type":
            return None
        if model_key == "Calling.Call":
            return list(filter(None, [getattr(instance.sender, "pk", None), getattr(instance.receiver, "pk", None)]))
        if model_key == "Calling.GroupCall":
            from Calling.models import GroupCallParticipant
            pks = [getattr(instance.creator, "pk", None)]
            for p in GroupCallParticipant.objects.filter(group_call=instance).select_related("user"):
                pks.append(getattr(p.user, "pk", None))
            return list(filter(None, set(pks)))
        if model_key == "Calling.GroupCallParticipant":
            pks = [getattr(instance.user, "pk", None)]
            if getattr(instance, "group_call_id", None) is not None:
                from Calling.models import GroupCall, GroupCallParticipant as GCP
                try:
                    gc = GroupCall.objects.get(pk=instance.group_call_id)
                    pks.append(getattr(gc.creator, "pk", None))
                    for p in GCP.objects.filter(group_call=gc).select_related("user"):
                        pks.append(p.user.pk)
                except Exception:
                    pass
            return list(filter(None, set(pks)))
        return None
    except Exception:
        return None

def _get_messaging_scope_ids(sender, instance, **kwargs):
    """
    Return list of chat_id or group_id (scope ids) for messaging GET cache invalidation.
    Used when a Messaging model is saved so we invalidate get:msg:<scope_id>:* for that chat/group.
    """
    scope_ids = []
    try:
        label = getattr(sender._meta, "label", None) or f"{sender._meta.app_label}.{sender._meta.model_name}"
        # GroupMessages -> group_id (instance.group_id is GroupChats.pk = group_id)
        if "GroupMessages" in label or sender._meta.model_name == "groupmessages":
            scope_id = getattr(instance, "group_id", None)
            if scope_id is not None:
                scope_ids.append(str(scope_id))
            return list(dict.fromkeys(scope_ids))
        # IndividualMessages -> chat_id (instance.chat_id is IndividualChats.pk = chat_id)
        if "IndividualMessages" in label or sender._meta.model_name == "individualmessages":
            scope_id = getattr(instance, "chat_id", None)
            if scope_id is not None:
                scope_ids.append(str(scope_id))
            return list(dict.fromkeys(scope_ids))
        # GroupChats -> group_id
        if "GroupChats" in label or sender._meta.model_name == "groupchats":
            scope_id = getattr(instance, "group_id", None)
            if scope_id is not None:
                scope_ids.append(str(scope_id))
            return scope_ids
        # GroupMembers -> groupchat_id is GroupChats.pk which is group_id
        if "GroupMembers" in label or sender._meta.model_name == "groupmembers":
            scope_id = getattr(instance, "groupchat_id", None)
            if scope_id is not None:
                scope_ids.append(str(scope_id))
            return list(dict.fromkeys(scope_ids))
        # IndividualChats -> chat_id
        if "IndividualChats" in label or sender._meta.model_name == "individualchats":
            scope_id = getattr(instance, "chat_id", None)
            if scope_id is not None:
                scope_ids.append(str(scope_id))
            return scope_ids
        # MessageAttachment -> group_message.group_id, individual_message.chat_id, or standalone group_id/chat_id
        if "MessageAttachment" in label or sender._meta.model_name == "messageattachment":
            gm = getattr(instance, "group_message", None)
            if gm is not None:
                sid = getattr(gm, "group_id", None) or (getattr(getattr(gm, "group", None), "group_id", None))
                if sid:
                    scope_ids.append(str(sid))
            im = getattr(instance, "individual_message", None)
            if im is not None:
                sid = getattr(im, "chat_id", None) or (getattr(getattr(im, "chat", None), "chat_id", None))
                if sid:
                    scope_ids.append(str(sid))
            if getattr(instance, "group_id", None) is not None:
                scope_ids.append(str(instance.group_id))
            if getattr(instance, "chat_id", None) is not None:
                scope_ids.append(str(instance.chat_id))
            return list(dict.fromkeys(scope_ids))
    except Exception:
        pass
    return scope_ids


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
        "get_functions_and_actionable_goals",
        "ActionableEntriesCoAuthor",
        "ActionableEntriesSharedWith",
    ],
    "QuaterlyReports.FunctionsEntriesShare": [
        "ActionableEntries",
        "get_functions_and_actionable_goals",
        "ActionableEntriesCoAuthor",
        "ActionableEntriesSharedWith",
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


def _invalidate_for_sender(sender, instance, **kwargs):
    # Messaging: invalidate by chat_id/group_id so all GETs for that chat/group are refreshed
    if sender._meta.app_label == "Messaging":
        scope_ids = _get_messaging_scope_ids(sender, instance, **kwargs)
        for scope_id in scope_ids:
            invalidate_get_cache_for_messaging_scope(scope_id)

    model_key = f"{sender._meta.app_label}.{sender._meta.model_name}"
    # Prefer label (App.ModelClass) so dict keys match; model_name is lowercase and would miss lookups
    prefixes = AFFECTED_GET_PREFIXES_BY_MODEL.get(getattr(sender._meta, "label", None))
    if prefixes is None:
        prefixes = AFFECTED_GET_PREFIXES_BY_MODEL.get(model_key)
    if prefixes is None:
        prefixes = PREFIXES_BY_APP.get(sender._meta.app_label, [])
    user_ids = _get_affected_user_ids(sender, instance, **kwargs)
    if not user_ids:
        return
    for prefix in prefixes:
        invalidate_get_cache_for_prefix(prefix, user_ids=user_ids)


def connect_cache_invalidation():
    """Call once at startup (e.g. from accounts.apps.ready()). Connects post_save to invalidate cache."""
    from events.models import BookSlot, Tour, Holiday, Event, Meeting, Room, BookingStatus, SlotMembers, tourmembers
    from Messaging.models import GroupChats, GroupMembers, IndividualChats, GroupMessages, IndividualMessages, MessageAttachment
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
        FunctionsEntriesShare,
        PlannedActions,
        SalesStatistics,
    )

    models_to_watch = [
        BookSlot, Tour, Holiday, Event, Meeting, Room, BookingStatus, SlotMembers, tourmembers,
        GroupChats, GroupMembers, IndividualChats, GroupMessages, IndividualMessages, MessageAttachment,
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
        FunctionsEntriesShare,
        PlannedActions,
        SalesStatistics,
        Call,
        GroupCall,
        GroupCallParticipant,
    ]
    for model in models_to_watch:
        post_save.connect(_invalidate_for_sender, sender=model)
        post_delete.connect(_invalidate_for_sender, sender=model)
