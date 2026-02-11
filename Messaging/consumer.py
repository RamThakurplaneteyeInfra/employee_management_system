import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import IndividualChats, IndividualMessages, GroupChats, GroupMessages
from asgiref.sync import sync_to_async
from django.shortcuts import get_object_or_404
from django.http import Http404, JsonResponse
from rest_framework import status
from accounts.filters import get_created_time_format

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.room_chat_name = f"chat_{self.chat_id}"
        user = self.scope["user"]

        # if user.is_anonymous:
        #     await self.close()
        #     print("User Not Found")
        #     return JsonResponse({"message":"User Not Found"},status=status.HTTP_404_NOT_FOUND)
        
        # allowed = await self.Validate_group_or_chat_id(user)

        # if not allowed:
        #     await self.close()
        #     print("Chat or Group Not Found")
        #     return JsonResponse({"message":"Chat or Group Not Found"},status=status.HTTP_404_NOT_FOUND)

        # Join room
        await self.channel_layer.group_add(self.room_chat_name,self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room
        await self.channel_layer.group_discard(self.room_chat_name,self.channel_name)

    async def receive(self, text_data):
        # message = data.get("message")
        message=text_data
        # sender = self.scope["user"]

        if not message:
            return JsonResponse({"message":"message Not Found"},status=status.HTTP_404_NOT_FOUND)

        # Save message into DB
        # is_saved=await self.save_message(sender.username, message)
        # if isinstance(is_saved,JsonResponse):
        #     return is_saved

        # Broadcast to group
        await self.channel_layer.group_send(
            self.room_chat_name,
            {
                "type": "chat_message",
                # "sender": sender.username,
                "message": message,
                # "at": get_created_time_format(is_saved.created_at),
            })

    async def chat_message(self, event):
        # Send message to WebSocket
        print(event)
        await self.send(text_data=json.dumps({
            # "sender": event["sender"],
            "message": event["message"]
        }))

    # @sync_to_async
    async def save_message(self, sender_username, message):
        try:
            sender = get_object_or_404(User,username=sender_username)
                
            # Group Chat
            if self.chat_id.startswith("G"):
                group = await GroupChats.objects.aget(group_id=self.chat_id)
                msg_obj=GroupMessages.objects.create(group=group,sender=sender,content=message)

            # Individual Chat
            else:
                chat = await IndividualChats.objects.aget(chat_id=self.chat_id)
                IndividualMessages.objects.create(chat=chat,sender=sender,content=message)
                
        except Http404 as e:
            print(e)
            return JsonResponse({"message":f"{e}"},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return JsonResponse({"message":f"{e}"},status=status.HTTP_304_NOT_MODIFIED)
        else:
            return msg_obj
            
    @sync_to_async
    def Validate_group_or_chat_id(self, user):
        if self.chat_id.startswith("G"):
            return GroupChats.objects.filter(group_id=self.chat_id).exists()

        return IndividualChats.objects.filter(chat_id=self.chat_id).filter().exists()
