from ems.urlImports import *
from . import views

sort_urls=[path("getBranch/",views.get_branches,name="sort"),
    path("getRoles/",views.get_roles,name="sort"),
    path("getDesignations/",views.get_designations,name="sort"),
    path("getDepartmentsandFunctions/",views.get_departments_and_functions,name="sort"),
    path("getTeamleads/",views.get_teamLeads,name="sort"),]

session_urls=[path('login/',views.user_login),
            path('logout/', views.user_logout),
            path('sessiondata/', views.get_session_data),]
employee_urls=[path('employee/dashboard/', views.employee_dashboard),
            path('employees/', views.get_all_employees),
            path('updateUsername/<slug:username>/', views.updateUsername),]

admin_urls= [
    path('', views.home, name='Home'),
    path('admin/updateProfile/<str:username>/', views.update_profile, name='users'),
    path('admin/createEmployeeLogin/', views.create_employee_login, name='users'),
    path('admin/deleteEmployee/<str:u>/', views.delete_user_profile, name='users'),
    path('admin/viewEmployee/<str:u>/', views.view_employee, name='users'),
    path('admin/changePassword/<str:u>/', views.changePassword, name='users'),
    path('admin/changePhoto/<str:username>/', views.update_photo, name='users'),
    path('admin/FetchPhoto/<str:username>/', views.FetchImage, name='users'),
]
urlpatterns =sort_urls+session_urls+employee_urls+admin_urls


