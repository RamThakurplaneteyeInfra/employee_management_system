from django.contrib import admin
from .models import BookSlot, Tour, Event, Meeting, Room, BookingStatus, SlotMembers,Holiday

admin.site.register(Room)
admin.site.register(BookingStatus)
admin.site.register(Holiday)
admin.site.register(BookSlot)
admin.site.register(SlotMembers)
admin.site.register(Tour)
admin.site.register(Event)


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("id", "meeting_type", "time", "meeting_room", "is_active", "created_at")
