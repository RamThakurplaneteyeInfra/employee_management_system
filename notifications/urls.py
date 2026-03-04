from django.urls import path
from .views import (
    get_notifications,
    mark_as_read,
    websocket_info,
    get_notification_types,
    cron_delete_seen_older_than_day,
    cron_delete_unseen_older_than_week,
)

urlpatterns = [
    path("today/", get_notifications),
    path("types/", get_notification_types),
    path("read/<int:pk>/", mark_as_read),
    # path("ws-info/", websocket_info),
    path("cron/delete-seen-older-than-day/", cron_delete_seen_older_than_day),
    path("cron/delete-unseen-older-than-week/", cron_delete_unseen_older_than_week),
]