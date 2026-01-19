from ems.urlImports import *
from . import views

sort_urls=[path("getBranch/",views.get_branches,name="sort"),
    path("getRoles/",views.get_roles,name="sort"),
    path("getDesignations/",views.get_designations,name="sort"),
    path("getDepartments/",views.get_departments,name="sort"),]
    # path("addMeetingHeadSubhead/",views.add_meeting_head_subhead,name="sort"),

session_urls=[path('login/', views.user_login),
            path('logout/', views.user_logout),
            path('sessiondata/', views.get_session_data),]
employee_urls=[path('employee/dashboard/', views.employee_dashboard),
            path('employees/', views.get_all_employees),]

admin_urls= [
    path('', views.home, name='Home'),
    path('admin/updateProfile/<slug:username>/', views.update_profile, name='users'),
    path('admin/createEmployeeLogin/', views.create_employee_login, name='users'),
    path('admin/deleteEmployee/<slug:u>/', views.delete_user_profile, name='users'),
    path('admin/viewEmployee/<slug:u>/', views.view_employee, name='users'),
    path('admin/changePassword/<slug:u>/', views.changePassword, name='users'),
]

urlpatterns =sort_urls+session_urls+employee_urls+admin_urls


