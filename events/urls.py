from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import rooms_dropdown
from .views import (
    BookSlotViewSet,
    TourViewSet,
    HolidayViewSet,
    EventViewSet,
)

router = DefaultRouter()
router.register("bookslots", BookSlotViewSet, basename="bookslots")
router.register("tours", TourViewSet, basename="tours")
router.register("holidays", HolidayViewSet, basename="holidays")
router.register("events", EventViewSet, basename="events")

urlpatterns = [
    path("rooms/", rooms_dropdown, name="rooms-dropdown"),
    path("", include(router.urls)),   # ✅ FIX
]