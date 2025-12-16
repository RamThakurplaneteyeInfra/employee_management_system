from django.conf import settings
from django.db import models
# from django.contrib.auth.models import 
from enum import Enum

# from django.db import models
from django.contrib.auth.models import User


class farm_emp_details(models.Model):
    class Meta:
        db_table='team_farm"."farm_employee_details'
        
    class Role(Enum):
        Employee= "Employee"
        Intern= "Intern"
        Team_Lead="TeamLead"
        none="None"
        
    class Team(Enum):
        Core = "Core"
        Tech = "Tech"
        none="None"
            
    emp_id=models.IntegerField(primary_key=True,null=False)
    emp_name=models.CharField(max_length=50,null=False)
    part_of=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Team],null=False)
    role=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Role],null=False)
    designation=models.CharField(max_length=50,null=True)
    email=models.CharField(max_length=50)
    file=models.FileField()


class infra_emp_details(models.Model):
    class Meta:
        db_table='team_infra"."infra_employee_details'
        
    class Role(Enum):
        Employee= "Employee"
        Intern= "Intern"
        Team_Lead="Team_Lead"
        none="None"
        
    class Team(Enum):
        Core = "Core"
        Tech = "Tech"
        none="None"
        
    emp_id=models.IntegerField(primary_key=True,null=False)
    emp_name=models.CharField(max_length=50,null=False)
    part_of=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Team],default=Team.none.value)
    role=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Role],default=Role.none.value)
    designation=models.CharField(max_length=50,null=True)
    email=models.CharField(max_length=50)
    file=models.FileField()
    
    
class team_manage(models.Model):
    class Meta:
        db_table='team_management"."management_team'
        
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
        ('TeamLead','TeamLead')
    )

    username= models.ForeignKey(User, on_delete=models.CASCADE,primary_key=True,db_column="username",to_field="username",related_name="accounts_profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"





