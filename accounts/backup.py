
# class EmployeeManager(BaseUserManager):
#     def create_user(self, username, password, Role, **extrafields):
#         extrafields['is_staff']=True
#         if not username or not password or not Role:
#             raise ValueError("Users must have a unique username, password and Role")
#         if Role=="Admin":
#             extrafields["is_superuser"]=True
#         else:
#             extrafields["is_superuser"]=False
#         user = self.model(username=username, password=password,role=Role,**extrafields)
#         user.set_password(password)
#         user.save(using=self._db)
#         return user
    
#     def create_superuser(self, username, password, role):
#         return self.create_user(username, password, role)
    

#             # Employee login details

# class Employee_login_details(AbstractBaseUser, PermissionsMixin):
    
#     class Role(Enum):
#         Admin="Admin"
#         TeamLead="TeamLead"
#         MD="MD"
#         Employee="Employee"
#         none="None"
#         Intern="Intern"
        
#     username = models.CharField(max_length=150, unique=True,primary_key=True)
#     password=models.CharField(max_length=150,null=False,unique=True)
#     role=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Role],default=Role.none.value)

#     objects = EmployeeManager()
#     USERNAME_FIELD = 'username'
#     REQUIRED_FIELDS = ['password','role']
#     def __str__(self):
#         return self.username
    
    
        # #Farm_emp_details
# class farm_emp_details(models.Model):
#     class Meta:
#         db_table='team_farm"."farm_employee_details'
        
#     class Role(Enum):
#         Employee= "Employee"
#         Intern= "Intern"
#         Team_Lead="TeamLead"
#         none="None"
        
#     class Team(Enum):
#         Core = "Core"
#         Tech = "Tech"
#         none="None"
            
#     emp_id=models.IntegerField(primary_key=True,null=False)
#     emp_name=models.CharField(max_length=50,null=False)
#     part_of=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Team],default=Team.none.value)
#     role=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Role],default=Role.none.value)
#     designation=models.CharField(max_length=50,null=True)
#     # password=models.CharField(max_length=50)
#     email=models.CharField(max_length=50)
#     file=models.FileField()
    
    
        # Infra_emp_details   
# class infra_emp_details(models.Model):
#     class Meta:
#         db_table='team_infra"."infra_employee_details'
        
#     class Role(Enum):
#         Employee= "Employee"
#         Intern= "Intern"
#         Team_Lead="Team_Lead"
#         none="None"
        
#     class Team(Enum):
#         Core = "Core"
#         Tech = "Tech"
#         none="None"
        
#     emp_id=models.IntegerField(primary_key=True,null=False)
#     emp_name=models.CharField(max_length=50,null=False)
#     # password=models.CharField(max_length=50)
#     part_of=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Team],default=Team.none.value)
#     role=models.CharField(max_length=20,choices=[(r.value, r.name.title()) for r in Role],default=Role.none.value)
#     designation=models.CharField(max_length=50,null=True)
#     email=models.CharField(max_length=50)
#     file=models.FileField()
    
    
        # Team management table
# class team_manage(models.Model):
#     class Meta:
#         db_table='team_management"."management_team'
        
#     class Role(Enum):
#         Admin = "Admin"
#         MD= "MD"
#         none="None"
        
#     emp_id=models.IntegerField(primary_key=True,null=False)
#     emp_name=models.CharField(max_length=50,null=False)
#     # password=models.CharField(max_length=50)
#     role=models.CharField( max_length=50,choices=[(r.value, r.name.title()) for r in Role],default=Role.none.value)
#     email=models.CharField(max_length=50)
#     file=models.FileField()

    # objects = EmployeeManager()
    # USERNAME_FIELD = 'username'
