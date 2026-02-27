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
from .urlImports import *
from .views import home
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls,name="Admin"),
    path("", home,name="Home"),
    path('accounts/', include('accounts.urls'),name="accounts"),
    path("tasks/",include("task_management.urls"),name="task_management"),
    path("messaging/", include("Messaging.urls"), name="Messaging"),
    path("", include("QuaterlyReports.urls"), name="QuaterlyReports"),
    path("notifications/", include("notifications.urls"), name="notifications"),
    path('adminapi/', include('adminpanel.urls'),name="adminpanelapi"),
    path('eventsapi/', include('events.urls'),name="eventsapi"),
]

if True:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    # print(type(settings.DEBUG))
    # print("debug is true")
