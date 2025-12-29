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
            
    Employee=models.OneToOneField(User, verbose_name="employee_id", on_delete=models.CASCADE,primary_key=True,null=False,db_column="Employee_id",to_field="username")
    Name=models.CharField(max_length=50,null=False,verbose_name="full_name")
    Team= models.CharField(verbose_name="team",max_length=20)
    Role= models.CharField(verbose_name="role",max_length=20)
    Designation=models.CharField(max_length=50,null=True,verbose_name="designation")
    Email_id=models.CharField(max_length=50,verbose_name="email_id")
    # File=models.FileField()
    Photo_link=models.ImageField(verbose_name="image_link",upload_to="profile_images/",blank=True,null=True,default=None)


class infra_emp_details(models.Model):
    class Meta:
        db_table='team_infra"."infra_employee_details'
        verbose_name = "Infra Employee "
        verbose_name_plural = "Infra Employees"
    
    Employee=models.OneToOneField(User, verbose_name="employee_id", on_delete=models.CASCADE,primary_key=True,null=False,db_column="Employee_id",to_field="username")
    Name=models.CharField(max_length=50,null=False,verbose_name="full_name")
    Team= models.CharField(verbose_name="team",max_length=20)
    Role= models.CharField(verbose_name="role",max_length=20)
    Designation=models.CharField(max_length=50,null=True,verbose_name="designation")
    Email_id=models.CharField(max_length=50,verbose_name="email_id")
    Photo_link=models.ImageField(verbose_name="image_link",upload_to="profile_images/",blank=True,null=True,default=None)
    
    
class team_manage(models.Model):
    class Meta:
        db_table='team_management"."management_team'
        verbose_name = "Management Team"
        verbose_name_plural = "Management Teams"
        
    Employee=models.OneToOneField(User, verbose_name="employee_id", on_delete=models.CASCADE,primary_key=True,null=False,db_column="Employee_id",to_field="username")
    Name=models.CharField(max_length=50,null=False,verbose_name="full_name")
    Role= models.CharField(verbose_name="role",max_length=20)
    Email_id=models.CharField(max_length=50,verbose_name="email_id")
    # file=models.FileField()
    Photo_link=models.ImageField(verbose_name="image_link",upload_to="profile_images/",blank=True,null=True,default=None)
    


class Profile(models.Model):

    Employee_id= models.OneToOneField(User,verbose_name="employee_id", on_delete=models.CASCADE,primary_key=True,db_column="Employee_id",to_field="username",related_name="accounts_profile")
    Role= models.CharField(verbose_name="role",max_length=20)
    Designation=models.CharField(verbose_name="designation",max_length=50,null=True)
    Branch= models.CharField(verbose_name="branch",max_length=50,null=True)
    Name=models.CharField(verbose_name="full_name",max_length=50,null=True)
    Email_id=models.EmailField(verbose_name="email_id",max_length=254,null=True)
    Date_of_birth=models.DateField(verbose_name="date_of_birth",auto_now=False, auto_now_add=False,null=True)
    Photo_link=models.ImageField(verbose_name="image_link", upload_to="profile_images/", height_field=None, width_field=None, max_length=None,null=True,blank=True)
    Date_of_join=models.DateField(verbose_name="date_of_joining",auto_now=False, auto_now_add=False,null=True)
    
    class Meta:
        verbose_name = "Employee Profile"
        verbose_name_plural = "Employees Profile"
    

    def __str__(self):
        return f"{self.Employee_id.username} - {self.Role}"
    
    
class Roles(models.Model):
    role_id=models.AutoField(primary_key=True,auto_created=True)
    role_name=models.CharField(max_length=20,unique=True,null=False)
    class Meta:
        db_table='team_management"."roles'
        verbose_name="role"
        # verbose_plural_name="roles"
    
class Designation(models.Model):
    class Meta:
        db_table='team_management"."designations'
        verbose_name="designation"
        # verbose_plural_name="designations"
        
    designation=models.CharField(max_length=50,unique=True,null=False)





