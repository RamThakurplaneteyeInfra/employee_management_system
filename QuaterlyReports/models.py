# from django.db import models
from accounts.models import *
from ems.verify_methods import *
from task_management.models import TaskStatus
from task_management.filters import get_taskStatus_object
from django.core.validators import MinValueValidator,MaxValueValidator

class Quaters(models.Model):
    """Quarter definition: label and start/end month range."""
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
    """Monthly department meeting head/subhead and sub-heads D1–D3 per department."""
    department=models.ForeignKey(Departments,on_delete=models.CASCADE,null=False,related_name="dapartment",db_column="department")
    # quater=models.ForeignKey(Quaters,on_delete=models.CASCADE,null=True,related_name="meeting_head_quater")
    month_of_the_quater=models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(3)])
    Meeting_head=models.CharField(max_length=200,null=False)
    meeting_sub_head=models.CharField(max_length=200,null=True,blank=True)
    Sub_Head_D1=models.CharField(max_length=200,null=True)
    Sub_Head_D2=models.CharField(max_length=200,null=True)
    Sub_Head_D3=models.CharField(max_length=200,null=True)
    
    
    @classmethod
    def create_head_and_subhead_for_each_dept(cls,dept:Departments,month_of_the_quater:int,
                                            Meeting_head:str,meeting_sub_head:str,Sub_Head_D1:str,
                                            Sub_Head_D2:str,Sub_Head_D3:str):
        
        obj=cls.objects.create(department=dept,month_of_the_quater=month_of_the_quater,
                            Meeting_head=Meeting_head,Sub_Head_D1=Sub_Head_D1,Sub_Head_D2=Sub_Head_D2,
                            Sub_Head_D3=Sub_Head_D3,meeting_sub_head=meeting_sub_head)
        return obj
    
    class Meta:
        db_table= 'team_management"."Monthly_department_wise_head_and_subhead'
        ...

class GRPS(models.Model):
    """Group code/label used in reports and sales stats."""
    grp=models.CharField(max_length=10)
    class Meta:
        db_table= 'quatery_reports"."GRP'
        ordering=["grp"]
class UsersEntries(models.Model):
    """User entry for a month/quarter: date, status, and note."""
    month_and_quater_id=models.ForeignKey(Monthly_department_head_and_subhead,on_delete=models.CASCADE,db_column="month_quater",null=False)
    user=models.ForeignKey(User,on_delete=models.CASCADE,to_field="username",db_column="Employee_id",null=False)
    date=models.DateField(auto_now=False,auto_now_add=False)
    status=models.ForeignKey(TaskStatus,editable=True,null=False,on_delete=models.CASCADE)
    note=models.TextField(null=False)
    
    class Meta:
        db_table= 'team_management"."UserEntries'

class FunctionsGoals(models.Model):
    """Goal linked to a function (main goal text)."""
    Function=models.ForeignKey(Functions,on_delete=models.CASCADE,db_column="function_id",verbose_name="function_id")
    Maingoal=models.CharField(max_length=100,null=False)
    
    class Meta:
        db_table= 'quatery_reports"."FunctionGoals'
        ordering=["Function"]

class ActionableGoals(models.Model):
    """Actionable sub-goal under a function goal: purpose and optional GRP."""
    FunctionGoal=models.ForeignKey(FunctionsGoals,on_delete=models.CASCADE,db_column="goal_id")
    purpose=models.CharField(max_length=255,null=False)
    grp=models.ForeignKey(GRPS,on_delete=models.CASCADE,null=True)
    class Meta:
        db_table= 'quatery_reports"."ActionableGoals'
        ordering=["FunctionGoal"]

class FunctionsEntries(models.Model):
    """Actionable entry: creator, co_author, approval and final status. Share chain in FunctionsEntriesShare."""
    goal = models.ForeignKey(ActionableGoals, on_delete=models.CASCADE, db_column="sub_goal_id", null=True)
    Creator = models.ForeignKey(User, on_delete=models.CASCADE, to_field="username", db_column="Employee_id", null=False)
    co_author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        to_field="username",
        db_column="co_author",
        null=True,
        blank=True,
        related_name="co_authored_entries",
    )
    approved_by_coauthor = models.BooleanField(default=False, db_column="approved_by_coauthor")
    date = models.DateField(auto_now=False, auto_now_add=False)
    time = models.TimeField(auto_now_add=True)
    final_Status = models.ForeignKey(
        TaskStatus,
        on_delete=models.CASCADE,
        editable=True,
        null=True,
        blank=True,
        related_name="functions_entries_final",
        db_column="status",
    )
    note = models.TextField()

    class Meta:
        db_table = 'quatery_reports"."FunctionsEntries'
        ordering = ["-date", "-time"]


class FunctionsEntriesShare(models.Model):
    """One link in the share chain: shared_with user, their note, shared_time, and individual_status."""
    actionable_entry = models.ForeignKey(
        FunctionsEntries,
        on_delete=models.CASCADE,
        related_name="share_chain",
        db_column="actionable_entry_id",
    )
    shared_with = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        to_field="username",
        db_column="shared_with",
        related_name="shared_entries_chain",
    )
    note = models.TextField(blank=True)
    shared_time = models.DateTimeField(auto_now_add=True)
    individual_status = models.ForeignKey(
        TaskStatus,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="functions_entries_share_status",
        db_column="individual_status_id",
    )

    class Meta:
        db_table = 'quatery_reports"."FunctionsEntriesShare'
        ordering = ["shared_time"]
        unique_together = [("actionable_entry", "shared_with")]

class PlannedActions(models.Model):
    """Placeholder / planned actions (fields commented out)."""
    # grp=models.ForeignKey(GRPS,on_delete=models.CASCADE,db_column="grp",null=False,verbose_name="grp")
    # action=models.TextField(null=False)
    # deadline=models.DateField(auto_now_add=False,auto_now=False)
    # assigned_to=models.ForeignKey(User,on_delete=models.CASCADE,db_column="assigned_to",null=False,verbose_name="assigned_help_to")
    # status=models.ForeignKey(TaskStatus,on_delete=models.CASCADE,db_column="status",null=False,verbose_name="status")
    
    # class Meta:
    #     db_table= 'quatery_reports"."PlannedActions'
    #     ordering=["grp","-deadline"]
    ...
class SalesStatistics(models.Model):
    """Sales stats per GRP: sale, calls, trial, demand, conversion, etc."""
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
