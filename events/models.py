from django.db import models
import datetime
from accounts.models import User

# ========================
# MASTER TABLES
# ========================


class Room(models.Model):
    """
    Meeting room (name and active flag) for slot bookings.
    Used by BookSlot and Meeting; list via GET /eventsapi/rooms/.
    """
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table='events"."Rooms'
        verbose_name="Room"
        verbose_name_plural = "rooms"

    def __str__(self):
        return self.name


class BookingStatus(models.Model):
    """
    Status of a booking (e.g. Confirmed, Cancelled, Done).
    Used by BookSlot.status; list via GET /eventsapi/status/.
    """
    status_name = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table='events"."BookingStatus'
        verbose_name="bookingstatus"

    def __str__(self):
        return self.status_name
class BookSlot(models.Model):
    """Booked slot: meeting title, date, time range, room, creator, and members (M2M)."""
    MEETING_TYPE_CHOICES = [("individual", "Individual"),("group", "Group Meeting"),]
    
    meeting_title = models.CharField(max_length=255)
    date=models.DateField(null=True)
    start_time=models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    room = models.ForeignKey(Room,on_delete=models.CASCADE,related_name="slotroom")
    description = models.TextField(blank=True, null=True)
    meeting_type = models.CharField(max_length=20,choices=MEETING_TYPE_CHOICES)
    status = models.ForeignKey(BookingStatus,on_delete=models.CASCADE,related_name="slotstatus",null=True,blank=True)
    notes = models.TextField(blank=True, null=True, help_text="Optional; required when status is set to Done.")
    # Optional "Schedule Hub done" text inputs (not required).
    need_more_discussion = models.TextField(blank=True, null=True)
    dispute = models.TextField(blank=True, null=True)
    in_future = models.TextField(blank=True, null=True)
    deliverable = models.TextField(blank=True, null=True)
    not_deliverable = models.TextField(blank=True, null=True)
    opportunity = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(User,on_delete=models.CASCADE,related_name="slotcreater",null=True)
    members=models.ManyToManyField(User,through="Slotmembers")
    class Meta:
        db_table='events"."Slots'
        verbose_name="Slot"
        ordering=["-date","-created_at"]
        indexes = [
            models.Index(fields=["-date", "-created_at"]),
        ]
        
    def __str__(self):
        return self.meeting_title


class SlotMembers(models.Model):
    """
    Through model linking BookSlot and User (members in a booked slot).
    One row per (slot, member); unique_together enforced.
    """
    slot = models.ForeignKey(BookSlot, on_delete=models.CASCADE, related_name="slotmembers")
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="inslots")
    
    class Meta:
        db_table='events"."SlotMember'
        verbose_name="Slotmember"
        unique_together = ("slot", "member")
        ordering=["slot"]


class Tour(models.Model):
    """
    Tour event: name, location, duration, dates, creator, and members (M2M).
    CRUD via /eventsapi/tours/.
    """
    tour_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    duration_days = models.PositiveIntegerField()
    starting_date = models.DateField(blank=True, null=True)
    members=models.ManyToManyField(User,through="tourMembers",related_name="tourmembers")
    created_by=models.ForeignKey(User,on_delete=models.CASCADE,null=True,related_name="tourcreator")
    # checkbox list (empty allowed)
    total_members=models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table='events"."Tour'
        verbose_name="tour"
        ordering=["-starting_date"]
    def __str__(self):
        return self.tour_name


class tourmembers(models.Model):
    """
    Through model linking Tour and User (members on a tour).
    unique_together (tour, member).
    """
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="tourmembers")
    member = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="intour")
    class Meta:
        db_table='events"."tourmembers'
        verbose_name="tourmember"
        unique_together = ("tour", "member")
        ordering=["tour"]
class Holiday(models.Model):
    """Company holiday: date, name, and fixed vs unfixed type."""
    FIXED = "fixed"
    UNFIXED = "unfixed"

    HOLIDAY_TYPE_CHOICES = [
        (FIXED, "Fixed"),
        (UNFIXED, "Unfixed"),
    ]

    date = models.DateField(unique=True)
    name = models.CharField(max_length=255)
    holiday_type = models.CharField(
        max_length=10,
        choices=HOLIDAY_TYPE_CHOICES,
        default=UNFIXED
    )
    
    class Meta:
    #     # Match original migration 0001; migration 0003 may have left table in task_management
        db_table = 'events"."Holiday'
    #     verbose_name = "holiday"
    #     verbose_name_plural = "holiday"
        ordering = ["date"]

    def __str__(self):
        return f"{self.name}-{self.date}"
class Event(models.Model):
    """
    Generic event: title, motive, date, and time.
    CRUD via /eventsapi/events/; create/update/delete restricted to Admin/MD/HR.
    """
    title = models.CharField(max_length=255, default="Untitled Event")
    motive = models.TextField(null=True)
    date = models.DateField()
    time = models.TimeField()
    
    class Meta:
        db_table='events"."event'
        verbose_name="Event"
        ordering=["date"]               

    def __str__(self):
        return self.title
class Reminder(models.Model):
    """
    Simple reminder attached to a user: title, date/time, optional note, and audit timestamps.
    Stored in the events schema.
    """
    title = models.TextField(null=False)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reminders",
        db_column="created_by_id",
    )

    class Meta:
        db_table = 'events"."Reminders'
        verbose_name = "reminder"
        verbose_name_plural = "reminders"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return self.title or f"Reminder {self.pk}"


class Meeting(models.Model):
    """
    Meeting push: product (FK), type, duration (minutes), room, active flag.
    CRUD via /eventsapi/meetingpush/; cron delete-previous-days via custom action.
    WebSocket may broadcast on product channel when product is set.
    """
    MEETING_TYPE_CHOICES = [("individual", "Individual"),("group", "Group Meeting"),]

    product = models.ForeignKey(
        "project.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meetings",
        db_column="product_id",
    )
    meeting_type=models.CharField(max_length=20, choices=MEETING_TYPE_CHOICES)
    time = models.SmallIntegerField(default=5)
    meeting_room = models.ForeignKey(Room,on_delete=models.CASCADE,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True,null=False)
    
    class Meta:
        db_table='events"."MeetingPush'
        ordering=["-created_at","is_active"]
    
    def __str__(self):
        room = getattr(self.meeting_room, "name", None) or ""
        prod = getattr(self.product, "name", None) or ""
        return f"Meeting {self.pk} — {prod} — {room}"
