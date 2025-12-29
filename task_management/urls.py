from django.urls import path
from . import views

urlpatterns = [
    path("get_employees_by_role_and_designation/",views.get_usernames_from_selected_role_and_desigantion,name="Tasks_management"),
    path("get_available_roles/",views.get_available_roles,name="Tasks_management"),
    path("create_task/",views.create_task,name="Tasks_management"),
    path("<int:task_id>/change_status/",views.change_status,name="Tasks_management"),
    path("view_tasks/",views.show_created_tasks,name="Tasks_management"),
    path("view_assigned_tasks/",views.show_assigned_tasks,name="Tasks_management"),
    path("",views.home,name="Tasks_management"),
]
