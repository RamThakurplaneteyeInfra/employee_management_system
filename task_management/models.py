from accounts.models import User,Profile
from django.db import models


class TaskTypes(models.Model):
    type_id=models.AutoField(primary_key=True,editable=False)
    type_name=models.CharField(unique=True,null=False,max_length=50)
    class Meta:
        db_table='task_management"."task_types'
        verbose_name="task_types"
        
    
class TaskStatus(models.Model):
    status_id=models.AutoField(primary_key=True,editable=False,auto_created=False,serialize=True)
    status_name=models.CharField(("task_status"), max_length=50,unique=True,default=None,null=False,editable=True)
    class Meta:
        db_table='task_management"."task_statuses'
        verbose_name="task_statuses"
    


class Task(models.Model):
    task_id=models.BigAutoField(primary_key=True,verbose_name="task_id",auto_created=True)
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=500,verbose_name="task_description",default=None)

    created_by = models.ForeignKey(
        User,
        related_name="created_tasks",
        on_delete=models.CASCADE,
        db_column="created_by",
        to_field="username",
    )
    assigned_to = models.ForeignKey(
        User,
        related_name="assigned_tasks",
        on_delete=models.CASCADE,
        db_column="assigned_to",
        to_field="username",
        
    )
    due_date=models.DateField(("due_date"), auto_now=False, auto_now_add=False)
    type=models.ForeignKey(TaskTypes, on_delete=models.CASCADE,null=False,db_column="task_type",related_name="task_type")
    status=models.ForeignKey(TaskStatus, verbose_name=("task_status"), on_delete=models.CASCADE,db_column="current_status",default=1,related_name="task_status")
    
    class Meta:
        db_table='task_management"."tasks'
        verbose_name="tasks"

    def __str__(self):
        return (self.title,self.task_id)
    
class TaskCreateAndEditLogs(models.Model):
    task=models.OneToOneField(Task, verbose_name=("task_id"), on_delete=models.CASCADE,db_column="task_id",primary_key=True,related_name="edit_logs")
    created_at=models.DateField(auto_now_add=True,db_index=True)
    created_time=models.TimeField(auto_now_add=True)
    last_edit_time=models.TimeField(auto_now=True)
    last_edit_date=models.DateField(auto_now=True)
    class Meta:
        db_table='Task_create_edit_logs'
        verbose_name="task_edit_create_log"
    
class TaskStatusChangeLogs(models.Model):
    task=models.OneToOneField(Task, verbose_name=("task_id"), on_delete=models.CASCADE,db_column="task_id",primary_key=True,related_name="status_change_log")
    last_status_change_date=models.DateField(auto_now=True)
    last_status_change_time=models.TimeField(auto_now=True)
    status_change_to=models.ForeignKey("task_management.TaskStatus", verbose_name=("change_to"), on_delete=models.CASCADE,db_column="change_to",null=False,related_name="status_change_log")
    class Meta:
        db_table="Task_status_changes_log"
        verbose_name="task_status_change_log"
    
    
    
    
    


# Create your models here.
