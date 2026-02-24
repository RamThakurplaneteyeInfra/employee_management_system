from django.urls import path
from .views import get_notifications, mark_as_read, websocket_info,get_notification_types

urlpatterns = [
    path("today/", get_notifications),
    path("types/", get_notification_types),
    path("read/<int:pk>/", mark_as_read),
    # path("ws-info/", websocket_info),
]