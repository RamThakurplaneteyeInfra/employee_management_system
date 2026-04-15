from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import JobOpeningViewSet

router = DefaultRouter()
router.register("jobs", JobOpeningViewSet, basename="jobs")

urlpatterns = [
    path("", include(router.urls)),
]
