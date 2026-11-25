from django.urls import path

from . import views

urlpatterns = [
    path("monthly/", views.monthly_attendance, name="attendance-monthly"),
    path("me/", views.my_attendance, name="attendance-me"),
    path("daily/", views.daily_attendance, name="attendance-daily"),
    path("daily-fixed/", views.daily_fixed_roster, name="attendance-daily-fixed"),
    path("health/", views.health_check, name="attendance-health"),
]
