from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import (
    AlertTypeViewSet,
    AlertViewSet,
    AnnouncementTypeViewSet,
    AnnouncementViewSet,
    AttentionViewSet,
)

router = DefaultRouter()
router.register("alert-types", AlertTypeViewSet, basename="alert-type")
router.register("alerts", AlertViewSet, basename="alert")
router.register("announcement-types", AnnouncementTypeViewSet, basename="announcement-type")
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("attention", AttentionViewSet, basename="attention")

urlpatterns = [
    path("", include(router.urls)),
]
