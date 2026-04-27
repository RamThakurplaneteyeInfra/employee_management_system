from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssetRequestViewSet


router = DefaultRouter()
router.register(r"requests", AssetRequestViewSet, basename="asset-request")

urlpatterns = [
    path("", include(router.urls)),
]

