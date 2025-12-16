from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    # path('CreateEmployee/', views.create_employee, name='create_employee'),
]