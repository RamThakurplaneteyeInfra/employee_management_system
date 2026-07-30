from django.urls import path

from .views import (
    ChecklistMdApprovalView,
    ChecklistPendingMdApprovalCountView,
    ChecklistPointsView,
    ProjectDetailView,
    ProjectListCreateView,
)

urlpatterns = [
    path("projects/checklist-points/", ChecklistPointsView.as_view(), name="deadline-checklist-points"),
    path(
        "projects/checklist-pending-md-approval/count/",
        ChecklistPendingMdApprovalCountView.as_view(),
        name="deadline-checklist-pending-md-count",
    ),
    path("projects/", ProjectListCreateView.as_view(), name="deadline-project-list-create"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="deadline-project-detail"),
    path(
        "projects/<int:pk>/phases/<int:phase_id>/checklist/<int:index>/md-approval/",
        ChecklistMdApprovalView.as_view(),
        name="deadline-checklist-md-approval",
    ),
]
