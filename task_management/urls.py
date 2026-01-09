from ems.urlImports import *
from . import views

task_filters=[path("getNamesfromRoleandDesignation/",views.get_Names_from_selected_role_and_desigantion,name="sort"),
    path("getTaskTypes/",views.get_types,name="sort")]

urlpatterns = [
    path("",views.home,name="Tasks_management"),
]
task_management=[path("createTask/",views.create_task,name="Tasks_management"),
    path("<int:id>/changeStatus/",views.change_status,name="Tasks_management"),
    path("<int:task_id>/updateTask/",views.update_task,name="Task_management"),
    path("viewTasks/",views.show_created_tasks,name="Tasks_management"),
    path("viewAssignedTasks/",views.show_assigned_tasks,name="Tasks_management"),
    path("<int:task_id>/deleteTask/",views.delete_task,name="Tasks_management"),]

task_messaging=[path("sendMessage/",views.post_task_message,name="sendMessage"),
                path("getMessage/<int:task_id>/",views.get_task_messages,name="getMessages")]

urlpatterns+=task_filters+task_messaging+task_management
