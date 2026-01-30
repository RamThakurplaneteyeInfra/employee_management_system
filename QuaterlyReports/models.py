from django.db import models
from accounts.models import *
from task_management.models import TaskStatus
from task_management.filters import get_taskStatus_object
from django.core.validators import MinValueValidator,MaxValueValidator

class Quaters(models.Model):
    quater=models.CharField(max_length=20,null=False,primary_key=True)
    start_month=models.IntegerField(null=True)
    end_month=models.IntegerField(null=True)
    
    @classmethod
    def create_quater(cls,quater:str,starting_month:int,ending_month:int):
        obj=cls.objects.create(quater=quater,start_month=starting_month,end_month=ending_month)
        return obj
    
    class Meta:
        db_table= 'team_management"."Quaters'
        verbose_name_plural = "quaters"
        ordering=["quater"]
    
class Monthly_department_head_and_subhead(models.Model):
    department=models.ForeignKey(Departments,on_delete=models.CASCADE,null=False,related_name="dapartment",db_column="department")
    quater=models.ForeignKey(Quaters,on_delete=models.CASCADE,null=False,related_name="meeting_head_quater")
    month_of_the_quater=models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(3)])
    Meeting_head=models.CharField(max_length=100,null=False)
    meeting_sub_head=models.CharField(max_length=100,null=True)
    Sub_Head_D1=models.CharField(max_length=100,null=True)
    Sub_Head_D2=models.CharField(max_length=100,null=True)
    Sub_Head_D3=models.CharField(max_length=100,null=True)
    
    
    @classmethod
    def create_head_and_subhead_for_each_dept(cls,quater:Quaters,dept:Departments,month_of_the_quater:int,
                                            Meeting_head:str,meeting_sub_head:str,Sub_Head_D1:str,
                                            Sub_Head_D2:str,Sub_Head_D3:str):
        
        obj=cls.objects.create(quater=quater,department=dept,month_of_the_quater=month_of_the_quater,
                            Meeting_head=Meeting_head,Sub_Head_D1=Sub_Head_D1,Sub_Head_D2=Sub_Head_D2,
                            Sub_Head_D3=Sub_Head_D3,meeting_sub_head=meeting_sub_head)
        return obj
    
    class Meta:
        db_table= 'team_management"."Monthly_department_wise_head_and_subhead'
        ...

class UsersEntries(models.Model):
    month_and_quater_id=models.ForeignKey(Monthly_department_head_and_subhead,on_delete=models.CASCADE,db_column="month_quater",null=False)
    user=models.ForeignKey(User,on_delete=models.CASCADE,to_field="username",db_column="Employee_id",null=False)
    date=models.DateField(auto_now=False,auto_now_add=False)
    status=models.ForeignKey(TaskStatus,editable=True,null=False,on_delete=models.CASCADE)
    note=models.TextField(null=False)
    
    class Meta:
        db_table= 'team_management"."UserEntries'

class FunctionsGoals(models.Model):
    Function=models.ForeignKey(Functions,on_delete=models.CASCADE,db_column="function_id",verbose_name="function_id")
    Maingoal=models.CharField(max_length=100,null=False)
    
    class Meta:
        db_table= 'quatery_reports"."FunctionGoals'
        ordering=["Function"]
    
class ActionableGoals(models.Model):
    FunctionGoal=models.ForeignKey(FunctionsGoals,on_delete=models.CASCADE,db_column="goal_id")
    purpose=models.CharField(max_length=100,null=False)
            
    class Meta:
        db_table= 'quatery_reports"."ActionableGoals'
        ordering=["FunctionGoal"]
    
class FunctionsEntries(models.Model):
    goal=models.ForeignKey(ActionableGoals,on_delete=models.CASCADE,db_column="sub_goal_id",null=True)
    Creator=models.ForeignKey(User,on_delete=models.CASCADE,to_field="username",db_column="Employee_id",null=False)
    date=models.DateField(auto_now=False,auto_now_add=False)
    status=models.ForeignKey(TaskStatus,on_delete=models.CASCADE,editable=True,null=False)
    note=models.TextField(null=False)
    class Meta:
        db_table= 'quatery_reports"."FunctionsEntries'
        ordering=["-date"]

class GRPS(models.Model):
    grp=models.CharField(max_length=10)
    
    class Meta:
        db_table= 'quatery_reports"."GRP'
        ordering=["grp"]
    
class PlannedActions(models.Model):
    grp=models.ForeignKey(GRPS,on_delete=models.CASCADE,db_column="grp",null=False,verbose_name="grp")
    action=models.TextField(null=False)
    deadline=models.DateField(auto_now_add=False,auto_now=False)
    assigned_to=models.ForeignKey(User,on_delete=models.CASCADE,db_column="assigned_to",null=False,verbose_name="assigned_help_to")
    status=models.ForeignKey(TaskStatus,on_delete=models.CASCADE,db_column="status",null=False,verbose_name="status")
    
    class Meta:
        db_table= 'quatery_reports"."PlannedActions'
        ordering=["grp","-deadline"]
class SalesStatistics(models.Model):
        grp=models.ForeignKey(GRPS,on_delete=models.CASCADE,db_column="grp",null=False,verbose_name="grp")
        Sale=models.IntegerField(null=True)
        Calls=models.IntegerField(null=True)
        Trial=models.IntegerField(null=True)
        Demand=models.IntegerField(null=True)
        Old_tgt=models.IntegerField(null=True)
        New_acq=models.IntegerField(null=True)
        Pitch=models.IntegerField(null=True)
        CP_ratio=models.CharField(null=True)
        Lead=models.IntegerField(null=True)
        Qual=models.IntegerField(null=True)
        Demo=models.IntegerField(null=True)
        Quote=models.IntegerField(null=True)
        Close=models.IntegerField(null=True)
        Conversion_percent=models.DecimalField(decimal_places=2,null=False,max_digits=6)
        status=models.ForeignKey(TaskStatus,on_delete=models.CASCADE,db_column="status",null=False,verbose_name="status",)
        
        class Meta:
            db_table= 'quatery_reports"."SalesStatistics'
            ordering=["grp"]
# Create your models here.

# data={"Marketing":[{"quater":"Q1","month":}]}