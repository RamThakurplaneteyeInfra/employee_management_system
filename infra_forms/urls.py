from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"boq-entries", views.BoqStructureEntryViewSet, basename="boq-structure-entry")
router.register(r"lidar-entries", views.LidarStructureEntryViewSet, basename="lidar-structure-entry")
router.register(r"sar-entries", views.SarStructureEntryViewSet, basename="sar-structure-entry")
router.register(r"projects", views.ProjectCatalogViewSet, basename="project-catalog")
router.register(r"project-forms", views.InfraProjectFormViewSet, basename="infra-project-form")

urlpatterns = [
    path("", include(router.urls)),
]
