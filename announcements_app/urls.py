from rest_framework.routers import DefaultRouter
from django.urls import include, path

from .views import AnnouncementPostViewSet

router = DefaultRouter()
router.register(r"", AnnouncementPostViewSet, basename="announcements-posts")

urlpatterns = [
    path("", include(router.urls)),
]

