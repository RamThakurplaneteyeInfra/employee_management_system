from django.db import models
from django.contrib.auth.models import User
import random
import string

def generate_chat_id(length=8):
    chat_id="C"
    chars = string.digits
    return chat_id+"".join(random.choices(chars, k=length))

def generate_group_id(length=5):
    chat_id="G"
    chars = string.digits
    return chat_id+"".join(random.choices(chars, k=length))

class GroupChats(models.Model):
    """Group chat room: name, description, creator, and last activity timestamp."""
    group_id = models.CharField(verbose_name="group_id",primary_key=True)
    group_name = models.CharField(max_length=100, blank=True,db_column="group_name",unique=True)
    description=models.TextField(max_length=200,null=True,verbose_name="description",db_column="description_of_group")
    participants=models.SmallIntegerField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_chats",db_column="created_by",to_field="username",verbose_name="created_groups"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(blank=True,null=True)
    last_message_at=models.DateTimeField(auto_now=True)
    class Meta:
        db_table='Groups'
        verbose_name="Group"
        indexes=[models.Index(fields=["created_by"])]
        ordering=["-last_message_at"]
        
    def __str__(self):
        return self.group_name or f"Chat-{self.created_by.accounts_profile.Name}"
    
    def can_delete_group(self,user):
        if user==self.created_by:
            return True
        else:
            return False
        
    def can_add_user(self,user):
        if user==self.created_by:
            return True
        else:
            return False
    
class GroupMembers(models.Model):
    """Membership of a user in a group chat; tracks seen state and unseen message count."""
    groupchat = models.ForeignKey(GroupChats, on_delete=models.CASCADE,related_name="group_members")
    participant= models.ForeignKey(User, on_delete=models.CASCADE,db_comment="participant",to_field="username",related_name="part_of_groups")
    seen=models.BooleanField(default=False)
    unseenmessages=models.SmallIntegerField(default=0)
    
    class Meta:
        db_table='GroupMembers'
        verbose_name="GroupMember"
        unique_together = ("groupchat", "participant")
        indexes=[models.Index(fields=["participant"])]
        ordering=["participant","unseenmessages"]
        
class IndividualChats(models.Model):
    """One-to-one conversation between two users (participant1 and participant2)."""
    chat_id=models.CharField(verbose_name="chat_id",primary_key=True)
    participant1=models.ForeignKey(User,to_field="username",verbose_name="participant1",db_column="user1",null=True,on_delete=models.SET_NULL,related_name="as_participant1")
    participant2=models.ForeignKey(User,to_field="username",verbose_name="participant2",db_column="user2",null=True,on_delete=models.SET_NULL,related_name="as_participant2")
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at=models.DateTimeField(auto_now=True)

    class Meta:
        db_table='UsersChats'
        unique_together = ("participant1", "participant2")
        indexes=[models.Index(fields=["participant1"])]
                #  models.Index(fields=["participant2"]),]
        ordering=["participant1","participant2","-last_message_at"]
        
    def get_other_participant(self, user):
        """Get the other participant in the conversation"""
        if user == self.participant1:
            return self.participant2
        return self.participant1
    
    def get_unread_count(self, user):
        """Get unread message count for a user"""
        return self.personal_messages.filter(
            sender=self.get_other_participant(user),
            seen=False
        ).count()
        
    @classmethod
    def get_or_create_indivisual_Chat(cls, user1:User, user2:User):
        """Get or create a conversation between two users"""
        # Ensure consistent ordering (smaller ID first)
        if user1.id > user2.id:
            user1, user2 = user2, user1
        try:
            obj=cls.objects.get(participant1=user1,participant2=user2)
            already_created=True
        except cls.DoesNotExist as e:
            chat_id=generate_chat_id()
            already_created=False
            obj=cls.objects.create(chat_id=chat_id,participant1=user1,participant2=user2)
        finally:
            return obj,already_created
        
class GroupMessages(models.Model):
    """Single message in a group chat: sender, content, optional tag; attachments reference this via MessageAttachment.group_message."""
    group = models.ForeignKey(GroupChats, on_delete=models.CASCADE, related_name="group_messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sended_group_messages")
    tag_to = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="taged_messages")
    deleted = models.BooleanField(default=False)
    edited = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(default=None, null=True, blank=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'GroupMessages'
        indexes = [models.Index(fields=["sender"])]
        ordering = ["group", "-created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.content[:20]}"

    def can_delete_message(self, user):
        return user == self.sender

    def can_edit_message(self, user):
        return user == self.sender


class IndividualMessages(models.Model):
    """Single message in a one-to-one chat; attachments reference this via MessageAttachment.individual_message."""
    chat = models.ForeignKey(IndividualChats, db_column="chat_id", null=False, related_name="personal_messages", on_delete=models.PROTECT)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, db_column="sender", to_field="username", null=False, related_name="sended_personal_messages")
    deleted = models.BooleanField(default=False)
    edited = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(default=None, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)
    content = models.TextField()

    class Meta:
        db_table = 'Chats'
        indexes=[models.Index(fields=["sender"])]
        ordering=["chat","-created_at"]
        
    def __str__(self):
        return f"{self.sender.username}: {self.content[:20]}"
    
    def can_delete_message(self,user):
        if user==self.sender:
            return True
        else:
            return False

class MessageAttachment(models.Model):
    """
    File or link in messaging. Either linked to a message (group_message or individual_message)
    or standalone in a conversation (group or chat set). Reference lives on the attachment,
    so unattached uploads have both message FKs null.
    """
    s3_key = models.CharField(max_length=512, db_column="s3_key", blank=True, null=True)
    file_name = models.CharField(max_length=255, db_column="file_name", blank=True, null=True)
    content_type = models.CharField(max_length=128, blank=True, null=True, db_column="content_type")
    file_size = models.PositiveIntegerField(null=True, blank=True, db_column="file_size")
    link_url = models.URLField(max_length=2048, db_column="link_url", blank=True, null=True)
    link_title = models.CharField(max_length=512, db_column="link_title", blank=True, null=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="uploaded_by",
        to_field="username",
        related_name="messaging_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column="created_at")
    # Linked to a message (attachment belongs to this message)
    group_message = models.ForeignKey(
        GroupMessages,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        db_column="group_message_id",
    )
    individual_message = models.ForeignKey(
        IndividualMessages,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        db_column="individual_message_id",
    )
    # Standalone in conversation (no message text)
    group = models.ForeignKey(
        GroupChats,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="standalone_attachments",
        db_column="group_id",
    )
    chat = models.ForeignKey(
        IndividualChats,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="standalone_attachments",
        db_column="chat_id",
    )

    class Meta:
        db_table = 'messaging"."MessageAttachments'
        verbose_name = "Message attachment"
        ordering = ["created_at"]

    @property
    def is_link(self):
        return bool(self.link_url)

    def __str__(self):
        if self.is_link:
            return f"Link: {self.link_title or self.link_url}"
        return f"{self.file_name or 'file'} ({self.s3_key or ''})"
