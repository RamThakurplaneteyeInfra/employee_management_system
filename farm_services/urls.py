from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FarmServiceRequestViewSet

router = DefaultRouter()
router.register(r"requests", FarmServiceRequestViewSet, basename="farm-service-request")

urlpatterns = [
    path("", include(router.urls)),
]

