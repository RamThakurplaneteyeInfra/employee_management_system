from django.urls import path
from .views import get_notifications, mark_as_read
 
urlpatterns = [
    path('notifications/', get_notifications),
    path('notifications/read/<int:pk>/', mark_as_read),
]