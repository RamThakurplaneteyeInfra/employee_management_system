from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='Home'),
    path('login/', views.user_login, name='login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('admin/updateProfile/', views.update_profile, name='update_profile'),
    path('admin/createEmployeeLogin/', views.create_employee_login, name='create_employee'),
    path('admin/employee/dashboard/<str:username>/', views.admin_employee_dashboard_view, name='employee_details'),
]

