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
    birthdaycounter_bulk,
)

router = DefaultRouter()
router.register("bookslots", BookSlotViewSet, basename="bookslots")
router.register("tours", TourViewSet, basename="tours")
router.register("holidays", HolidayViewSet, basename="holidays")
router.register("events", EventViewSet, basename="events")
router.register("rooms", RoomViewSet, basename="rooms")
router.register("status", BookingStatusViewset, basename="status")
router.register("meetingpush",MeetingViewSet , basename="meetingpush")

# Birthday counter routes must come before router so "events/birthdaycounter/" is not matched by events/<pk>/ (pk="birthdaycounter")
urlpatterns = [
    path("events/birthdaycounter/", birthdaycounter_bulk),  # POST with body {"users": ["u1", "u2", ...]}
    path("events/birthdaycounter/<str:username>/", birthdaycounter, name="birthday"),
    path("", include(router.urls)),
]