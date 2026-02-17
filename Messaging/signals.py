from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import *
from notifications.models import Notification,notification_type
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@receiver(post_save, sender=GroupMessages)
def create_notification_for_groupmessage(sender, instance:GroupMessages, created, **kwargs):
    group_obj=instance.group
    group_mem=GroupMembers.objects.filter(groupchat=group_obj).exclude(participant=instance.sender)
    notification_type_obj=notification_type.objects.get(type_name="Group_message")
    
    if created:
        for i in group_mem:
            obj=Notification.objects.create(from_user=instance.sender,receipient=i.participant,message=instance.content,type_of_notification=notification_type_obj)
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{i.participant.username}",
                {
                    "type": "send_notification",
                    "title": f"{obj.type_of_notification.type_name} from {group_obj.group_name}",
                    "message":obj.message
                }
            )
            
@receiver(post_save, sender=IndividualMessages)
def create_notification_for_chatmessage(sender, instance:IndividualMessages, created, **kwargs):
    # group_mem=GroupMembers.objects.filter(GroupChats)
    notification_type_obj=notification_type.objects.get(type_name="private_message")
    
    if created:
        sender=instance.sender
        other_user=instance.chat.get_other_participant(user=sender)
        obj=Notification.objects.create(from_user=instance.sender,receipient=other_user,message=instance.content,type_of_notification=notification_type_obj)
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{other_user.username}",
            {
                "type": "send_notification",
                "title": f"{obj.type_of_notification.type_name} from {sender}",
                "message":obj.message
            }
        )