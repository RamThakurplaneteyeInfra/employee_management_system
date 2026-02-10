from accounts.models import User,Profile
from django.db import models
from datetime import datetime
class TaskTypes(models.Model):
    type_id=models.AutoField(primary_key=True,editable=False)
    type_name=models.CharField(unique=True,null=False,max_length=50)
    class Meta:
        db_table='task_management"."task_types'
        verbose_name="task_type"
        verbose_name_plural = "task_types"

class TaskStatus(models.Model):
    status_id=models.AutoField(primary_key=True,editable=False,auto_created=False,serialize=True)
    status_name=models.CharField(("task_status"), max_length=50,unique=True,default=None,null=False,editable=True)
    class Meta:
        db_table='task_management"."task_statuses'
        verbose_name="task_status"
        verbose_name_plural = "task_statuses"

class Task(models.Model):
    task_id=models.BigAutoField(primary_key=True,verbose_name="task_id",auto_created=True)
    title = models.CharField(max_length=200,null=False)
    description = models.TextField(max_length=500,verbose_name="task_description",default=None,null=True)

    created_by = models.ForeignKey(
        User,
        related_name="created_tasks",
        on_delete=models.CASCADE,
        db_column="created_by",
        to_field="username",
    )
    assignees=models.ManyToManyField(User,through="TaskAssignies",related_name="assigned_tasks")
    due_date=models.DateField(("due_date"), auto_now=False, auto_now_add=False)
    type=models.ForeignKey(TaskTypes, on_delete=models.CASCADE,null=False,db_column="task_type",related_name="task_type")
    status=models.ForeignKey(TaskStatus, verbose_name=("task_status"), on_delete=models.CASCADE,db_column="current_status",default=1,related_name="task_status")
    created_at=models.DateTimeField(auto_now_add=True,null=True)
    class Meta:
        db_table='task_management"."tasks'
        verbose_name="task"
        verbose_name_plural = "tasks"
        ordering=["-created_by"]

    def __str__(self):
        return f"task-id-{self.task_id}"
    
class TaskAssignies(models.Model):
    task=models.ForeignKey(Task,db_column="task_id",null=False,on_delete=models.CASCADE,related_name="tasks")
    assigned_to=models.ForeignKey(User,db_column="assigned_to",null=False,on_delete=models.CASCADE,to_field="username",related_name="Tasks_assigned")
    class Meta:
        db_table='task_management"."tasksAssignee'
        verbose_name="taskAssignee"
        verbose_name_plural = "tasksAssignees"
        unique_together = ("task", "assigned_to")
        ordering=["task"]

    def __str__(self):
        if self.task:
            total=TaskAssignies.objects.filter(task=self.task).count()
            return f"task-id:{self.task.task_id}\ntotal_assignees:{total}"
        return "None"
    
class TaskCreateAndEditLogs(models.Model):
    task=models.OneToOneField(Task, verbose_name=("task_id"), on_delete=models.CASCADE,db_column="task_id",primary_key=True,related_name="task_edit_logs")
    created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    last_edit=models.DateTimeField(auto_now=True)
    class Meta:
        db_table='task_management"."Task_create_edit_logs'
        verbose_name="task_edit_create_log"
        ordering=["-last_edit"]
    ...
    
class TaskStatusChangeLogs(models.Model):
    task=models.OneToOneField(Task, verbose_name=("task_id"), on_delete=models.CASCADE,db_column="task_id",primary_key=True,related_name="status_change_logs")
    created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    last_edit=models.DateTimeField(auto_now=True)
    status_change_to=models.ForeignKey("task_management.TaskStatus", verbose_name=("change_to"), on_delete=models.CASCADE,db_column="change_to",null=False,related_name="status_change_log")
    class Meta:
        db_table='task_management"."Task_status_changes_log'
        verbose_name="task_status_change_log"
        ordering=["-last_edit"]
    ...
    
class AssingnedTasksCount(models.Model):
    assignee=models.OneToOneField(User,primary_key=True,db_column="employee_id",to_field="username",on_delete=models.CASCADE)
    count_SOS=models.IntegerField(db_column="total_SOS",default=0,)
    count_1_Day=models.IntegerField(db_column="total_1_Day",default=0)
    count_10_Day=models.IntegerField(db_column="total_10_Day",default=0)
    count_Monthly=models.IntegerField(db_column="total_Monthly",default=0)
    count_Quaterly=models.IntegerField(db_column="total_Quaterly",default=0)
    class Meta:
        db_table="Assigned_tasks_count_by_type"
        verbose_name="Assigned_tasks_count_by_type"
        ordering=["-count_SOS","-count_1_Day"]
        
class CreatedTasksCount(models.Model):
    creator=models.OneToOneField(User,primary_key=True,db_column="employee_id",to_field="username",on_delete=models.CASCADE)
    count_SOS=models.IntegerField(db_column="total_SOS",default=0,)
    count_1_Day=models.IntegerField(db_column="total_1_Day",default=0)
    count_10_Day=models.IntegerField(db_column="total_10_Day",default=0)
    count_Monthly=models.IntegerField(db_column="total_Monthly",default=0)
    count_Quaterly=models.IntegerField(db_column="total_Quaterly",default=0)
    class Meta:
        db_table='task_management"."Created_tasks_count_by_type'
        verbose_name="Created_tasks_count_by_type"
        ordering=["-count_SOS","-count_1_Day"]
        
class TaskMessage(models.Model):
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE,db_index=True,db_column="sender",to_field="username",default="753"
    )
    message = models.TextField(verbose_name="message",null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # update_at=models.DateTimeField(auto_now=True)
    seen=models.BooleanField(default=False)
    
    class Meta:
        db_table='task_management"."taskmessaging'
        verbose_name="taskmessaging"
        ordering=["sender","-created_at"]
        
    def __str__(self):
        return f"{self.sender.username}: {self.message[:30]}"
# Insert rows into db tables through models instances
# TaskTypes.objects.create(type_name="1 Day")
# TaskTypes.objects.create(type_name="SOS")
# TaskTypes.objects.create(type_name="10 Day")
# TaskTypes.objects.create(type_name="Monthly")
# TaskTypes.objects.create(type_name="Quaterly")
# TaskStatus.objects.create(status_name="PENDING")
# TaskStatus.objects.create(status_name="COMPLETED")
# TaskStatus.objects.create(status_name="INPROCESS")