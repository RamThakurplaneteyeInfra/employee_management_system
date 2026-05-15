from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssetViewSet, calendar_summary, health

router = DefaultRouter()
router.register(r"assets", AssetViewSet, basename="asset")

urlpatterns = [
    path("health/", health, name="asset_management_health"),
    path("calendar-summary/", calendar_summary, name="asset_management_calendar_summary"),
    path("", include(router.urls)),
]
