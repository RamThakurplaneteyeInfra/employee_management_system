"""
Task management signals: counts, logs, and WebSocket notifications.

Important: Django dispatches signals synchronously. Receivers must be sync functions.
Async receivers are never awaited, so notification/WebSocket would never run.
"""
import logging
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from accounts.filters import _get_users_Name_sync
from ems.utils import gmt_to_ist_str

from .models import Task, TaskAssignies, AssingnedTasksCount, CreatedTasksCount, TaskCreateAndEditLogs, TaskMessage
from notifications.models import Notification, notification_type

logger = logging.getLogger(__name__)


def _add_task_count_for_assignee_sync(sender, created, instance: TaskAssignies, **kwargs):
    if not created:
        return
    user = instance.assigned_to
    try:
        obj = AssingnedTasksCount.objects.get(assignee=user)
    except AssingnedTasksCount.DoesNotExist:
        obj = AssingnedTasksCount.objects.create(assignee=user)
    for i in ["1 Day", "SOS", "10 Day", "Monthly", "Quaterly"]:
        if instance.task.type.type_name == i:
            value = getattr(obj, "count_" + i.replace(" ", "_"), 0)
            setattr(obj, "count_" + i.replace(" ", "_"), value + 1)
            obj.save()
            break


@receiver(post_save, sender=TaskAssignies)
def add_task_count_for_assignee(sender, created, instance: TaskAssignies, **kwargs):
    _add_task_count_for_assignee_sync(sender, created, instance, **kwargs)


def _add_task_count_for_creator_sync(sender, created, instance: Task, **kwargs):
    if not created:
        return
    user = instance.created_by
    try:
        obj = CreatedTasksCount.objects.get(creator=user)
    except CreatedTasksCount.DoesNotExist:
        obj = CreatedTasksCount.objects.create(creator=user)
    for i in ["1 Day", "SOS", "10 Day", "Monthly", "Quaterly"]:
        if instance.type.type_name == i:
            value = getattr(obj, "count_" + i.replace(" ", "_"), 0)
            setattr(obj, "count_" + i.replace(" ", "_"), value + 1)
            obj.save()
            break


@receiver(post_save, sender=Task)
def add_task_count_for_creator(sender, created, instance: Task, **kwargs):
    _add_task_count_for_creator_sync(sender, created, instance, **kwargs)


def _task_edit_and_create_logs_sync(sender, created, instance: Task, **kwargs):
    if created:
        TaskCreateAndEditLogs.objects.create(task=instance)


@receiver(post_save, sender=Task)
def task_edit_and_create_logs(sender, created, instance: Task, **kwargs):
    _task_edit_and_create_logs_sync(sender, created, instance, **kwargs)


def _task_assigned_notification_sync(sender, created, instance: TaskAssignies, **kwargs):
    """Notify assignee when they are assigned to a task."""
    if not created:
        return
    assignee = instance.assigned_to
    task = instance.task
    creator = task.created_by
    creator_name=_get_users_Name_sync(creator)
    msg = f"New task '{task.title}' assigned to you"
    try:
        nt = notification_type.objects.get(type_name="Task_Created")
    except notification_type.DoesNotExist:
        return
    notification_obj=Notification.objects.create(
        from_user=creator,
        receipient=assignee,
        message=msg,
        type_of_notification=nt,
    )
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{assignee.username}",
        {"type": "send_notification", "title": f"New task Assigned", "category": "Task_Created", "message": msg, "extra": {"time": gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")}},
    )


@receiver(post_save, sender=TaskAssignies)
def task_assigned_notification(sender, created, instance: TaskAssignies, **kwargs):
    _task_assigned_notification_sync(sender, created, instance, **kwargs)

def _task_message_notification_sync(sender, created, instance: TaskMessage, **kwargs):
    """When a task message is created, notify all assigned members (excluding the sender)."""
    if not created:
        return
    task = instance.task
    sender_user = instance.sender
    sender_name = _get_users_Name_sync(sender_user)
    message_preview = (instance.message[:20] + "…") if len(instance.message) > 20 else instance.message
    msg = message_preview
    try:
        nt = notification_type.objects.get(type_name="Task_Message")
    except notification_type.DoesNotExist:
        nt = None
    assignees = TaskAssignies.objects.filter(task=task).select_related("assigned_to")
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    for ta in assignees:
        assignee = ta.assigned_to
        if assignee == sender_user:
            continue
        try:
            if nt:
                notification_obj = Notification.objects.create(
                    from_user=sender_user,
                    receipient=assignee,
                    message=msg,
                    type_of_notification=nt,
                )
                extra_time = gmt_to_ist_str(notification_obj.created_at, "%d/%m/%Y, %H:%M:%S")
            else:
                extra_time = gmt_to_ist_str(timezone.now(), "%d/%m/%Y, %H:%M:%S")
            async_to_sync(channel_layer.group_send)(
                f"user_{assignee.username}",
                {
                    "type": "send_notification",
                    "title": f"Task Message for the task '{task.title}'",
                    "from": sender_name,
                    "category": "Task_Message",
                    "message": msg,
                    "extra": {"time": extra_time},
                },
            )
        except Exception as e:
            logger.warning("Task message WebSocket notification failed for assignee %s: %s", assignee.username, e)


@receiver(post_save, sender=TaskMessage)
def task_message_notification(sender, created, instance: TaskMessage, **kwargs):
    _task_message_notification_sync(sender, created, instance, **kwargs)
