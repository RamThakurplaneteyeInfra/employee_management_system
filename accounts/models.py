from django.conf import settings
from django.db import models
# from django.contrib.auth.models import 
from enum import Enum
from django.contrib.auth.models import User


class farm_emp_details(models.Model):
    class Meta:
        db_table='team_farm"."farm_employee_details'
        verbose_name = "Farm Employee "
        verbose_name_plural = "Farm Employees"
        
    class Role(Enum):
        Employee= "Employee"
        Intern= "Intern"
        Team_Lead="TeamLead"
        none="None"
        
    class Team(Enum):
        Core = "Core"
        Tech = "Tech"
        none="None"
            
    Emp_id=models.IntegerField(primary_key=True,null=False)
    Emp_name=models.CharField(max_length=50,null=False)
    Part_of=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Team],null=False)
    role=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Role],null=False)
    Designation=models.CharField(max_length=50,null=True)
    Email=models.CharField(max_length=50)
    File=models.FileField()


class infra_emp_details(models.Model):
    class Meta:
        db_table='team_infra"."infra_employee_details'
        verbose_name = "Infra Employee "
        verbose_name_plural = "Infra Employees"
        
    class Role(Enum):
        Employee= "Employee"
        Intern= "Intern"
        Team_Lead="Team_Lead"
        none="None"
        
    class Team(Enum):
        Core = "Core"
        Tech = "Tech"
        none="None"
        
    Emp_id=models.IntegerField(primary_key=True,null=False)
    Emp_name=models.CharField(max_length=50,null=False)
    Part_of=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Team],default=Team.none.value)
    role=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Role],default=Role.none.value)
    Designation=models.CharField(max_length=50,null=True)
    Email=models.CharField(max_length=50)
    File=models.FileField()
    
    
class team_manage(models.Model):
    class Meta:
        db_table='team_management"."management_team'
        verbose_name = "Management Team"
        verbose_name_plural = "Management Teams"
        
    class Role(Enum):
        Admin = "Admin"
        MD= "MD"
        none="None"
        
    emp_id=models.IntegerField(primary_key=True,null=False)
    emp_name=models.CharField(max_length=50,null=False)
    role=models.CharField( max_length=50,choices=[(r.value, r.name.title()) for r in Role],default=Role.none.value)
    email=models.CharField(max_length=50)
    file=models.FileField()

# from django.db import models
# from django.contrib.auth.models import User


class Profile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('employee', 'Employee'),
        ('MD','MD'),
        ('TeamLead','TeamLead'),
        ('Intern','Intern')
    )

    Employee_id= models.OneToOneField(User,verbose_name="emp_id", on_delete=models.CASCADE,primary_key=True,db_column="Employee_id",to_field="username",related_name="accounts_profile")
    Role= models.CharField(verbose_name="emp_role",max_length=10, choices=ROLE_CHOICES,null=True)
    Designation=models.CharField(verbose_name="emp_designation",max_length=50,null=True)
    Branch= models.CharField(verbose_name="emp_branch",max_length=50,null=True)
    Name=models.CharField(verbose_name="emp_full_name",max_length=50,null=True)
    Email_id=models.EmailField(verbose_name="emp_email_id",max_length=254,null=True)
    Date_of_birth=models.DateField(verbose_name="emp_date_of_birth",auto_now=False, auto_now_add=False,null=True)
    Photo_link=models.ImageField(verbose_name="emp_image", upload_to="profile_images/", height_field=None, width_field=None, max_length=None,null=True,blank=True)
    Date_of_join=models.DateField(verbose_name="emp_date_of_joining",auto_now=False, auto_now_add=False,null=True)
    
    class Meta:
        verbose_name = "Employee Profile"
        verbose_name_plural = "Employee Profiles"
    

    def __str__(self):
        return f"{self.Employee_id.username} - {self.Role}"





