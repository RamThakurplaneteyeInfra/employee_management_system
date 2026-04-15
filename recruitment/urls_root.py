"""
Same JobOpening API at site root: /jobs/ … (alias for clients that omit /api/).

URL names use basename ``jobs_root`` so they do not clash with ``recruitment.urls`` (``jobs-list`` under /api/).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import JobOpeningViewSet

router = DefaultRouter()
router.register("jobs", JobOpeningViewSet, basename="jobs_root")

urlpatterns = [
    path("", include(router.urls)),
]
