from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='Home'),
    path('login/', views.user_login, name='login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('admin/employees/dashboard/', views.employee_dashboard, name='all_employee_dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('admin/updateProfile/', views.update_profile, name='update_profile'),
    path('admin/createEmployeeLogin/', views.create_employee_login, name='create_profile'),
    path('admin/deleteEmployee/<str:u>/', views.delete_user_profile, name='delete_profile'),
    path('admin/employees/dashboard/<str:username>/', views.admin_employee_dashboard_view, name='employee_details'),
]

