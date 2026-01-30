from django.db import models

# ========================
# MASTER TABLES
# ========================

class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # is_active = models.BooleanField(default=True)

    class Meta:
        db_table='events"."Rooms'
        verbose_name_plural = "rooms"
        
    def __str__(self):
        return self.name


class BookingStatus(models.Model):
    status_name= models.CharField(max_length=20, unique=True)
    # label = models.CharField(max_length=50)
    # is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table='events"."BookingStatus'
        verbose_name_plural = "Bookingstatuses"

    def __str__(self):
        return self.status_name

# ========================
# 1. BOOK SLOT
# ========================

class BookSlot(models.Model):
    date_time = models.DateTimeField()
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="bookings"
    )
    
    booking_type = models.CharField(max_length=20)  
    # Individual / Group (can be blank later)
    title = models.TextField()
    status = models.ForeignKey(
        BookingStatus,
        on_delete=models.CASCADE,
        related_name="bookings"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table='events"."BookingSlots'
        verbose_name_plural = "BookingSlots"
        

# ========================
# 2. TOUR
# ========================

class Tour(models.Model):
    tour_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    duration_days = models.PositiveIntegerField()
    members = models.JSONField(blank=True, null=True)
    # checkbox list (empty allowed)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table='events"."Tours'
        verbose_name_plural = "tours"

    def __str__(self):
        return self.tour_name

# ========================
# 3. HOLIDAY
# ========================

class Holiday(models.Model):
    FIXED = "fixed"
    UNFIXED = "unfixed"

    HOLIDAY_TYPE_CHOICES = [
        (FIXED, "Fixed"),
        (UNFIXED, "Unfixed"),
    ]

    date = models.DateField()
    name = models.CharField(max_length=255)
    holiday_type = models.CharField(
        max_length=10,
        choices=HOLIDAY_TYPE_CHOICES,
        default=UNFIXED
    )
    
    class Meta:
        db_table='events"."Holidays'
        verbose_name_plural = "Holidays"

    def __str__(self):
        return f"{self.name} ({self.date})"

# ========================
# 4. EVENTS
# ========================

class Event(models.Model):
    date_time = models.DateTimeField()
    motive = models.TextField()
    
    class Meta:
        db_table='events"."Event'
        verbose_name_plural = "events"
