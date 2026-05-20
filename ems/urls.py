"""
URL configuration for ems project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from attendance.views import daily_attendance
from .urlImports import *
from .views import home, metrics_view
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls,name="Admin"),
    path("", home,name="Home"),
    path("metrics", metrics_view, name="metrics"),
    path('accounts/', include('accounts.urls'),name="accounts"),
    path("tasks/",include("task_management.urls"),name="task_management"),
    path("messaging/", include("Messaging.urls"), name="Messaging"),
    path("", include("QuaterlyReports.urls"), name="QuaterlyReports"),
    path("notifications/", include("notifications.urls"), name="notifications"),
    path('adminapi/', include('adminpanel.urls'),name="adminpanelapi"),
    path('eventsapi/', include('events.urls'),name="eventsapi"),
    path('clientsapi/', include('Clients.urls'), name="clientsapi"),
    path('customerpanelapi/', include('CustomerPanel.urls'), name="customerpanelapi"),
    path("projectapi/", include("project.urls"), name="project"),
    path("deadline/", include("projects_deadline.urls"), name="projects_deadline"),
    path("alertsapi/", include("Alerts_Announcements.urls"), name="alerts_announcements"),
    path("api/announcements/", include("announcements_app.urls"), name="announcements_app_api"),
    path("notesapi/", include("notes.urls"), name="notesapi"),
    # Asset booking / scheduling API (mount before recruitment's broader `api/` include)
    path("api/asset-management/", include("asset_management.urls"), name="asset_management_api"),
    # Spec alias for daily attendance (GET-only, same handler as /attendanceapi/daily/)
    path(
        "api/v1/attendance/daily-fixed/",
        daily_attendance,
        name="attendance_daily_fixed",
    ),
    # Recruitment: /api/jobs/ (canonical) and /jobs/ (alias for legacy / misconfigured clients)
    path("api/", include("recruitment.urls"), name="recruitment"),
    path("", include("recruitment.urls_root")),
    path("attendanceapi/", include("attendance.urls"), name="attendance"),
    # AI task summaries (Groq): isolated app, write-only to its own table.
    path("api/ai/summary/", include("ai_summary.urls"), name="ai_summary_api"),
    # AI EMS insight (aggregates + Grok); also mounted at /ai/ for spec alias
    path("api/ai/", include("insight.urls"), name="insight_api_ai"),
    path("ai/", include("insight.urls"), name="insight_ai"),
    # INFRA structure forms API (same routes as standalone backend, under /api/infra/)
    path("api/infra/", include("infra_forms.urls"), name="infra_forms_api"),
    # Asset / Software requests (TeamLead/HR/Admin/MD only)
    path("api/assets-request/", include("assets_request.urls"), name="assets_request_api"),
    # Tour advance requests (separate from eventsapi/tours/ team tours)
    path("api/tour-advance/", include("tour_advance.urls"), name="tour_advance_api"),
]

if True:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    # print(type(settings.DEBUG))
    # print("debug is true")
