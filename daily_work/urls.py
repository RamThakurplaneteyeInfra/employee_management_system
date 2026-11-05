from django.urls import path

from .views import (
    DailyReportView,
    EmployeeListView,
    InternListView,
    MarkReportsSeenView,
    MyProjectListView,
    ProjectDetailView,
    ProjectListCreateView,
    UnseenReportCountView,
)

urlpatterns = [
    path("employees/", EmployeeListView.as_view(), name="daily_work_employees"),
    path("interns/", InternListView.as_view(), name="daily_work_interns"),
    path("projects/", ProjectListCreateView.as_view(), name="daily_work_projects"),
    path(
        "projects/<int:project_id>/",
        ProjectDetailView.as_view(),
        name="daily_work_project_detail",
    ),
    path("my-projects/", MyProjectListView.as_view(), name="daily_work_my_projects"),
    path("reports/", DailyReportView.as_view(), name="daily_work_reports"),
    path(
        "reports/mark-seen/",
        MarkReportsSeenView.as_view(),
        name="daily_work_reports_mark_seen",
    ),
    path(
        "reports/unseen-count/",
        UnseenReportCountView.as_view(),
        name="daily_work_reports_unseen_count",
    ),
]
