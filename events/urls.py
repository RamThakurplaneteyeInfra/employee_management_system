from rest_framework.routers import DefaultRouter
from django.urls import path, include


from .views import (
    BookSlotViewSet,
    TourViewSet,
    HolidayViewSet,
    EventViewSet,
    RoomViewSet,
    BookingStatusViewset,
    MeetingViewSet,
    holidays_ping,
    birthdaycounter,
)

router = DefaultRouter()
router.register("bookslots", BookSlotViewSet, basename="bookslots")
router.register("tours", TourViewSet, basename="tours")
router.register("holidays", HolidayViewSet, basename="holidays")
router.register("events", EventViewSet, basename="events")
router.register("rooms", RoomViewSet, basename="rooms")
router.register("status", BookingStatusViewset, basename="status")
router.register("meetingpush",MeetingViewSet , basename="meetingpush")

urlpatterns = [
    # path("holidays-ping", holidays_ping),
    # path("holidays-ping/", holidays_ping),
    path("", include(router.urls)),
    path('events/birthdaycounter/<str:username>/', birthdaycounter, name='birthday'),
]