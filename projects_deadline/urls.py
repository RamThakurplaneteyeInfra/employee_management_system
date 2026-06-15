from django.urls import path

from .views import ChecklistPointsView, ProjectDetailView, ProjectListCreateView

urlpatterns = [
    path("projects/checklist-points/", ChecklistPointsView.as_view(), name="deadline-checklist-points"),
    path("projects/", ProjectListCreateView.as_view(), name="deadline-project-list-create"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="deadline-project-detail"),
]
