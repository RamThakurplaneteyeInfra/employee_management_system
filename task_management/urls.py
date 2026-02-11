from ems.urlImports import *
from . import views

task_filters=[path("getNamesfromRoleandDesignation/",views.get_Names_from_selected_role_and_desigantion,name="sort"),
    path("getTaskTypes/",views.get_types,name="sort"),
    path("getTaskStatuses/",views.get_all_TaskStatuses,name="sort")]

urlpatterns = [
    path("",views.home,name="Tasks_management"),
]
task_management=[path("createTask/",views.create_task,name="Tasks_management"),
    path("changeStatus/<int:task_id>/",views.change_status,name="Tasks_management"),
    path("updateTask/<int:task_id>/",views.update_task,name="Task_management"),
    path("viewTasks/",views.show_created_tasks,name="Tasks_management"),
    path("viewAssignedTasks/",views.show_assigned_tasks,name="Tasks_management"),
    path("deleteTask/<int:task_id>/",views.delete_task,name="Tasks_management"),
    path("Taskcount/<slug:username>/",views.get_task_count_from_username,name="Tasks_management"),]

task_messaging=[path("sendMessage/",views.post_task_message,name="sendMessage"),
                path("getMessage/<int:task_id>/",views.get_task_messages,name="getMessages")]

urlpatterns+=task_filters+task_messaging+task_management
