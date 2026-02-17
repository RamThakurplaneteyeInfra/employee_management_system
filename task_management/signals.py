import os
from django.db.models.signals import post_delete,post_save,pre_save,post_init
from .models import *
from django.dispatch import receiver
from notifications.models import Notification,notification_type
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@receiver(post_save, sender=TaskAssignies)
def add_task_count_for_Assignee(sender,created, instance:TaskAssignies, **kwargs):
    if created:
        user=instance.assigned_to
        try:
            obj=AssingnedTasksCount.objects.get(assignee=user)
        except AssingnedTasksCount.DoesNotExist:
            obj=AssingnedTasksCount.objects.create(assignee=user)
            for i in ["1 Day","SOS","10 Day","Monthly","Quaterly"]:
                if instance.task.type.type_name==i:
                    value=getattr(obj,"count_"+i.replace(" ","_"))
                    setattr(obj,"count_"+i.replace(" ","_"),value+1)
                    obj.save()
                    break
        else:
            for i in ["1 Day","SOS","10 Day","Monthly","Quaterly"]:
                if instance.task.type.type_name==i:
                    value=getattr(obj,"count_"+i.replace(" ","_"))
                    setattr(obj,"count_"+i.replace(" ","_"),value+1)
                    obj.save()
                    break
                
@receiver(post_save, sender=Task)
def add_task_count_for_Assignee(sender,created, instance:Task, **kwargs):
    if created:
        user=instance.created_by
        try:
            obj=CreatedTasksCount.objects.get(creator=user)
        except CreatedTasksCount.DoesNotExist:
            obj=CreatedTasksCount.objects.create(creator=user)
            for i in ["1 Day","SOS","10 Day","Monthly","Quaterly"]:
                if instance.type.type_name==i:
                    value=getattr(obj,"count_"+i.replace(" ","_"))
                    setattr(obj,"count_"+i.replace(" ","_"),value+1)
                    obj.save()
                    break
        else:
            for i in ["1 Day","SOS","10 Day","Monthly","Quaterly"]:
                if instance.type.type_name==i:
                    value=getattr(obj,"count_"+i.replace(" ","_"))
                    setattr(obj,"count_"+i.replace(" ","_"),value+1)
                    obj.save()
                    break
            
@receiver(post_save, sender=Task)
def task_edit_and_create_logs(sender,created,instance:Task, **kwargs):
    if created:
        TaskCreateAndEditLogs.objects.create(task=instance)

@receiver(post_save, sender=Task)
def task_status_change_logs(sender,instance:Task, **kwargs):
    ...

@receiver(post_save, sender=Task)
def task_assigned_notification(sender, instance:Task, created, **kwargs):
    # tasks = Task.objects.prefetch_related('assignees').filter(id=instance.task_id)
    assignee=instance.assignees.all()
    Notification_obj=notification_type.objects.get(type_name="Task_Created")

    if created and assignee:
        for i in assignee:
            print(i)
            obj=Notification.objects.create(from_user=instance.created_by,receipient=i,message=f"task created by {instance.created_by.username}",
                                            type_of_notification=Notification_obj)
            
#         # realtime push
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{i.username}",
                {
                    "type": "send_notification",
                    "title": obj.type_of_notification.type_name,
                    "message": obj.message,
                }
            )

