from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TourAdvanceRequestViewSet

router = DefaultRouter()
router.register(r"requests", TourAdvanceRequestViewSet, basename="tour-advance-request")

urlpatterns = [
    path("", include(router.urls)),
]
