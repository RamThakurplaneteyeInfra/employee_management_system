from rest_framework.routers import DefaultRouter
from django.urls import path, include


from .views import *

router = DefaultRouter()
router.register("bookslots", BookSlotViewSet, basename="bookslots")
router.register("tours", TourViewSet, basename="tours")
router.register("holidays", HolidayViewSet, basename="holidays")
router.register("events", EventViewSet, basename="events")
router.register("rooms", RoomViewSet, basename="rooms")
router.register("status", BookingStatusViewset, basename="status")
router.register("meetingpush",MeetingViewSet , basename="meetingpush")

urlpatterns = [
    path("", include(router.urls))
]