"""
Task management signals: counts, logs, and WebSocket notifications.
"""
from asgiref.sync import sync_to_async, async_to_sync
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer

from .models import Task, TaskAssignies, AssingnedTasksCount, CreatedTasksCount, TaskCreateAndEditLogs
from notifications.models import Notification, notification_type


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
async def add_task_count_for_assignee(sender, created, instance: TaskAssignies, **kwargs):
    await sync_to_async(_add_task_count_for_assignee_sync)(sender, created, instance, **kwargs)


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
async def add_task_count_for_creator(sender, created, instance: Task, **kwargs):
    await sync_to_async(_add_task_count_for_creator_sync)(sender, created, instance, **kwargs)


def _task_edit_and_create_logs_sync(sender, created, instance: Task, **kwargs):
    if created:
        TaskCreateAndEditLogs.objects.create(task=instance)


@receiver(post_save, sender=Task)
async def task_edit_and_create_logs(sender, created, instance: Task, **kwargs):
    await sync_to_async(_task_edit_and_create_logs_sync)(sender, created, instance, **kwargs)


def _task_assigned_notification_sync(sender, created, instance: TaskAssignies, **kwargs):
    """Notify assignee when they are assigned to a task."""
    if not created:
        return
    assignee = instance.assigned_to
    task = instance.task
    creator = task.created_by
    msg = f"New task '{task.title}' assigned to you by {creator.username}"
    try:
        nt = notification_type.objects.get(type_name="Task_Created")
    except notification_type.DoesNotExist:
        return
    Notification.objects.create(
        from_user=creator,
        receipient=assignee,
        message=msg,
        type_of_notification=nt,
    )
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{assignee.username}",
        {"type": "send_notification", "title": "Task Assigned", "message": msg, "extra": {"task_id": task.task_id}},
    )


@receiver(post_save, sender=TaskAssignies)
async def task_assigned_notification(sender, created, instance: TaskAssignies, **kwargs):
    await sync_to_async(_task_assigned_notification_sync)(sender, created, instance, **kwargs)
