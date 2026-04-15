from django.urls import path

from . import views

urlpatterns = [
    path("monthly/", views.monthly_attendance, name="attendance-monthly"),
    path("me/", views.my_attendance, name="attendance-me"),
    path("health/", views.health_check, name="attendance-health"),
]
