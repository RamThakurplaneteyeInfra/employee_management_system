from django.urls import path

from . import views

urlpatterns = [
    path("run/", views.run_summary, name="ai_summary_run"),
    path("latest/", views.latest_summary, name="ai_summary_latest"),
]

