from django.urls import path

from . import views

urlpatterns = [
    path("ems-insight/", views.ems_insight, name="ems_insight"),
]
