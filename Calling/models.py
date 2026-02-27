from django.db import models
from accounts.models import User
class Call(models.Model):
    """Model for audio/video calls between users."""
    AUDIO = "audio"
    VIDEO = "video"
    CALL_TYPE_CHOICES = [(AUDIO, "Audio"), (VIDEO, "Video")]

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    ENDED = "ended"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (DECLINED, "Declined"),
        (ENDED, "Ended"),
    ]

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="initiated_calls",
        to_field="username",
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_calls",
        to_field="username",
    )
    call_type = models.CharField(max_length=10, choices=CALL_TYPE_CHOICES)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=PENDING
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messaging"."Calls'
        verbose_name = "Call"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.call_type})"


class GroupCall(models.Model):
    """Model for group audio/video calls (multiple participants)."""
    AUDIO = "audio"
    VIDEO = "video"
    CALL_TYPE_CHOICES = [(AUDIO, "Audio"), (VIDEO, "Video")]

    ACTIVE = "active"
    ENDED = "ended"
    STATUS_CHOICES = [(ACTIVE, "Active"), (ENDED, "Ended")]

    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_group_calls",
        to_field="username",
    )
    call_type = models.CharField(max_length=10, choices=CALL_TYPE_CHOICES)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messaging"."GroupCalls'
        verbose_name = "Group call"
        ordering = ["-created_at"]

    def __str__(self):
        return f"GroupCall #{self.pk} ({self.call_type}) by {self.creator.username}"


class GroupCallParticipant(models.Model):
    """Participant in a group call (invited or joined)."""
    INVITED = "invited"
    JOINED = "joined"
    LEFT = "left"
    STATUS_CHOICES = [
        (INVITED, "Invited"),
        (JOINED, "Joined"),
        (LEFT, "Left"),
    ]

    group_call = models.ForeignKey(
        GroupCall,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="group_call_participations",
        to_field="username",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=INVITED
    )
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'messaging"."GroupCallParticipants'
        verbose_name = "Group call participant"
        unique_together = [["group_call", "user"]]
        ordering = ["group_call", "user"]

    def __str__(self):
        return f"{self.user.username} in GroupCall #{self.group_call_id} ({self.status})"

# Create your models here.
