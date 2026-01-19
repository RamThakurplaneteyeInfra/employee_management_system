from django.conf import settings
from django.db import models
from django.contrib.auth.models import BaseUserManager,AbstractUser,AbstractBaseUser
from enum import Enum
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator,validate_email
from datetime import date

# class farm_emp_details(models.Model):
    # class Meta:
    #     db_table='team_farm"."farm_employee_details'
    #     verbose_name = "Farm Employee"
    #     verbose_name_plural = "Farm Employees"
            
    # Employee=models.OneToOneField(User, verbose_name="employee_id", on_delete=models.CASCADE,primary_key=True,null=False,db_column="Employee_id",to_field="username")
    # Name=models.CharField(max_length=50,null=False,verbose_name="full_name")
    # Team= models.CharField(verbose_name="team",max_length=20)
    # Role= models.CharField(verbose_name="role",max_length=20)
    # Designation=models.CharField(max_length=50,null=True,verbose_name="designation")
    # Email_id=models.CharField(max_length=50,verbose_name="email_id")
    # Photo_link=models.ImageField(verbose_name="image_link",upload_to="profile_images/",blank=True,null=True,default=None)

# class infra_emp_details(models.Model):
    # class Meta:
    #     db_table='team_infra"."infra_employee_details'
    #     verbose_name = "Infra Employee "
    #     verbose_name_plural = "Infra Employees"
    
    # Employee=models.OneToOneField(User, verbose_name="employee_id", on_delete=models.CASCADE,primary_key=True,null=False,db_column="Employee_id",to_field="username")
    # Name=models.CharField(max_length=50,null=False,verbose_name="full_name")
    # Team= models.CharField(verbose_name="team",max_length=20)
    # Role= models.CharField(verbose_name="role",max_length=20)
    # Designation=models.CharField(max_length=50,null=True,verbose_name="designation")
    # Email_id=models.CharField(max_length=50,verbose_name="email_id")
    # Photo_link=models.ImageField(verbose_name="image_link",upload_to="profile_images/",blank=True,null=True,default=None)
    
# class team_manage(models.Model):
    # class Meta:
    #     db_table='team_management"."management_team'
    #     verbose_name = "Management Team"
    #     verbose_name_plural = "Management Teams"
        
    # Employee=models.OneToOneField(User, verbose_name="employee_id", on_delete=models.CASCADE,primary_key=True,null=False,db_column="Employee_id",to_field="username")
    # Name=models.CharField(max_length=50,null=False,verbose_name="full_name")
    # Role= models.CharField(verbose_name="role",max_length=20)
    # Email_id=models.CharField(max_length=50,verbose_name="email_id")
    # Photo_link=models.ImageField(verbose_name="image_link",upload_to="profile_images/",blank=True,null=True,default=None)

# A model for "Roles" table
class Roles(models.Model):
    role_id=models.AutoField(primary_key=True,auto_created=True)
    role_name=models.CharField(max_length=20,unique=True,null=True)
    total_count=models.IntegerField(default=0,null=False,verbose_name="count")
    class Meta:
        db_table='team_management"."roles'
        verbose_name="role"
        verbose_name_plural="roles"
        
# A model for "Branches" table
class Branch(models.Model):
    branch_id=models.SmallAutoField(primary_key=True,auto_created=True,verbose_name="id",editable=False)
    branch_name=models.CharField(max_length=25,unique=True,null=True,verbose_name="branch")
    class Meta:
        db_table='team_management"."Branches'
        verbose_name="branch"
        verbose_name_plural="branches"
        
# # A model for "Designations" table
class Designation(models.Model):
    class Meta:
        db_table='team_management"."designations'
        verbose_name="designation"
        verbose_name_plural="designations"
    designation=models.CharField(max_length=50,unique=True,null=True)
    total_count=models.IntegerField(default=0,null=False,verbose_name="count")

# A model for "Profiles" table
class Profile(models.Model):

    Employee_id= models.OneToOneField(User,verbose_name="employee_id", on_delete=models.CASCADE,primary_key=True,db_column="Employee_id",to_field="username",related_name="accounts_profile",db_index=True)
    Role= models.ForeignKey(Roles,verbose_name="role",on_delete=models.CASCADE,db_column="Role",related_name="Employee_roles",null=True)
    Designation=models.ForeignKey("Designation",verbose_name="designation",db_column="Designation",on_delete=models.CASCADE,related_name="designations",null=True)
    Branch= models.ForeignKey("Branch",verbose_name="branch",on_delete=models.CASCADE,db_column="Branch",related_name="branches",null=True)
    Name=models.CharField(verbose_name="full_name",max_length=50,null=True)
    Email_id=models.EmailField(verbose_name="email_id",max_length=254,unique=True,validators=[validate_email])
    Date_of_birth=models.DateField(verbose_name="date_of_birth",auto_now=False, auto_now_add=False,null=True)
    Photo_link=models.ImageField(verbose_name="image_link", upload_to="profile_images/", height_field=None, width_field=None, max_length=None,null=True,blank=True)
    Date_of_join=models.DateField(verbose_name="date_of_joining",auto_now=False, auto_now_add=False,null=True)
    Department=models.ForeignKey("Departments",verbose_name="department",db_column="department",on_delete=models.CASCADE,related_name="department",null=True)
    class Meta:
        verbose_name = "Employee Profile"
        verbose_name_plural = "Employees Profile"
        ordering=["-Name"]
        indexes = [
        models.Index(fields=['Role',"Designation"]),
    ]
        
    def __str__(self):
        return f"{self.Employee_id.username} - {self.Role}"
    
# A model for "Management_Profiles" table
class management_Profile(models.Model):
    Employee=models.OneToOneField(User,on_delete=models.PROTECT,to_field="username",null=False,related_name="management")
    Role= models.ForeignKey(Roles,verbose_name="role",on_delete=models.CASCADE,db_column="Role",related_name="management_roles",null=True)
    Name=models.CharField(verbose_name="full_name",max_length=50,null=True)
    Email_id=models.EmailField(verbose_name="email_id",max_length=254,unique=True,validators=[validate_email])
    Date_of_birth=models.DateField(verbose_name="date_of_birth",auto_now=False, auto_now_add=False,null=True)
    Photo_link=models.ImageField(verbose_name="image_link", upload_to="profile_images/", height_field=None, width_field=None, max_length=None,null=True,blank=True)
    Date_of_join=models.DateField(verbose_name="date_of_joining",auto_now=False, auto_now_add=False,null=True)

    class Meta:
        db_table='team_management"."management_profiles'
        verbose_name="management_profile"
        ordering=["-Date_of_join","Role"]
    def __str__(self):
        return f"{self.Role.role_name}-{self.Name}"
    
class Departments(models.Model):
    dept_name=models.CharField(max_length=50,unique=True,null=False)
    count=models.SmallIntegerField(default=0)
    
    @classmethod
    def add_department(cls,dept_name:str):
        obj=cls.objects.create(dept_name=dept_name)
        return obj 
    
    class Meta:
        db_table= 'team_management"."Departments'
        verbose_name_plural = "departments"
        ordering=["dept_name"]

    ...
    
class Quaters(models.Model):
    quater=models.CharField(max_length=20,null=False,primary_key=True)
    # starting_month=models.IntegerField(null=True)
    # ending_month=models.IntegerField(null=True)
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
    # quater_with_financial_year=models.ForeignKey(Financial_years_Quaters_Mapping,on_delete=models.CASCADE,null=False,related_name="quater",db_column="quater")
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
    
# obj=Quaters.create_quater(quater="Q3",starting_month=9,ending_month=12)
# Financial_years_Quaters_Mapping.add_quaterwise_year(quater=obj,financial_year_start=2026,financial_year_end=2027)
# Roles.objects.create(role_name="Admin")  
# Roles.objects.create(role_name="MD")        
# Roles.objects.create(role_name="Employee")        
# Roles.objects.create(role_name="Intern")        
# Roles.objects.create(role_name="TeamLead")        

# Branch.objects.create(branch_name="Farm Core")
# Branch.objects.create(branch_name="Farm Tech")
# Branch.objects.create(branch_name="Infra Core")
# Branch.objects.create(branch_name="Infra Tech")
# Branch.objects.create(branch_name="Technology")

# Designation.objects.create(designation="Python Developer")
# Designation.objects.create(designation="AI/ML Developer")
# Designation.objects.create(designation="Web Developer")
# Designation.objects.create(designation="Backend Developer")
# Designation.objects.create(designation="Precision Agriculture Manager")
# Designation.objects.create(designation="Digital Marketing Manager")
# Designation.objects.create(designation="Project Supervisor")
# Designation.objects.create(designation="Designer Engineer")
# Designation.objects.create(designation="Site Engineer")
# Designation.objects.create(designation="Field Officer")





