from django.db import models
from django.contrib.auth.models import User
from django.core.validators import validate_email
from datetime import timedelta
# A model for "Roles" table
class Roles(models.Model):
    """User role (e.g. Admin, MD); used for permissions and counts."""
    role_id=models.AutoField(primary_key=True,auto_created=True)
    role_name=models.CharField(max_length=20,unique=True,null=True)
    total_count=models.IntegerField(default=0,null=False,verbose_name="count")
    class Meta:
        db_table='team_management"."roles'
        verbose_name="role"
        verbose_name_plural="roles"
        
# A model for "Branches" table
class Branch(models.Model):
    """Office/branch location."""
    branch_id=models.SmallAutoField(primary_key=True,auto_created=True,verbose_name="id",editable=False)
    branch_name=models.CharField(max_length=25,unique=True,null=True,verbose_name="branch")
    class Meta:
        db_table='team_management"."Branches'
        verbose_name="branch"
        verbose_name_plural="branches"
        
# # A model for "Designations" table
class Designation(models.Model):
    """Job designation/title; used in profiles and counts."""
    designation=models.CharField(max_length=50,unique=True,null=True)
    total_count=models.IntegerField(default=0,null=False,verbose_name="count")
    class Meta:
        db_table='team_management"."designations'
        verbose_name="designation"
        verbose_name_plural="designations"

# Through table for Profile <-> Functions (many-to-many). Stored in login_details schema.
class ProfileFunction(models.Model):
    profile = models.ForeignKey(
        "Profile",
        on_delete=models.CASCADE,
        db_column="employee_id",
        to_field="Employee_id",
        related_name="profile_functions",
    )
    function = models.ForeignKey(
        "Functions",
        on_delete=models.CASCADE,
        db_column="function_id",
        related_name="profile_functions",
    )

    class Meta:
        db_table = 'login_details"."profile_functions'
        unique_together = ("profile", "function")
        verbose_name = "Profile function"
        verbose_name_plural = "Profile functions"


# A model for "Profiles" table
class Profile(models.Model):
    """Employee profile: name, role, branch, department, team lead, and optional functions (M2M)."""

    Employee_id= models.OneToOneField(User,verbose_name="employee_id", on_delete=models.CASCADE,primary_key=True,db_column="Employee_id",to_field="username",related_name="accounts_profile",db_index=True)
    Role= models.ForeignKey(Roles,verbose_name="role",on_delete=models.CASCADE,db_column="Role",related_name="Employee_roles",null=True)
    Designation=models.ForeignKey("Designation",verbose_name="designation",db_column="Designation",on_delete=models.CASCADE,related_name="designations",null=True)
    Branch= models.ForeignKey("Branch",verbose_name="branch",on_delete=models.CASCADE,db_column="Branch",related_name="branches",null=True)
    Name=models.CharField(verbose_name="full_name",max_length=50,null=True,unique=True)
    Email_id=models.EmailField(verbose_name="email_id",max_length=254,unique=True,validators=[validate_email])
    Date_of_birth=models.DateField(verbose_name="date_of_birth",auto_now=False, auto_now_add=False,null=True)
    Photo_link=models.ImageField(verbose_name="image_link", upload_to="Employee_Photo/", height_field=None, width_field=None, max_length=None,null=True,blank=True)
    Date_of_join=models.DateField(verbose_name="date_of_joining",auto_now=False, auto_now_add=False,null=True)
    Department=models.ForeignKey("Departments",verbose_name="department",db_column="department",on_delete=models.CASCADE,related_name="department",null=True)
    Teamlead=models.ForeignKey(User,on_delete=models.CASCADE,related_name="teamlead",null=True,verbose_name="teamlead",default=None,db_column="teamlead")
    functions = models.ManyToManyField(
        "Functions",
        through="ProfileFunction",
        related_name="profiles",
        blank=True,
        verbose_name="functions",
    )
    birthday_counter=models.SmallIntegerField(default=0)
    class Meta:
        verbose_name = "Employee Profile"
        verbose_name_plural = "Employees Profile"
        ordering=["Name"]
        indexes = [models.Index(fields=['Role',"Designation"]),]
        
    def __str__(self):
        return f"{self.Employee_id.username} - {self.Role}"
    
# A model for "Management_Profiles" table
class management_Profile(models.Model):
    """Management-specific profile subset (role, name, email, DOB, join date, photo)."""
    Employee=models.OneToOneField(User,on_delete=models.CASCADE,to_field="username",null=False,related_name="management")
    Role= models.ForeignKey(Roles,verbose_name="role",on_delete=models.CASCADE,db_column="Role",related_name="management_roles",null=True)
    Name=models.CharField(verbose_name="full_name",max_length=50,null=True)
    Email_id=models.EmailField(verbose_name="email_id",max_length=254,unique=True,validators=[validate_email])
    Date_of_birth=models.DateField(verbose_name="date_of_birth",auto_now=False, auto_now_add=False,null=True)
    Photo_link=models.ImageField(verbose_name="image_link", upload_to="Employee_Photo/", height_field=None, width_field=None, max_length=None,null=True,blank=True)
    Date_of_join=models.DateField(verbose_name="date_of_joining",auto_now=False, auto_now_add=False,null=True)

    class Meta:
        db_table='team_management"."management_profiles'
        verbose_name="management_profile"
        ordering=["-Date_of_join","Role"]
    def __str__(self):
        return f"{self.Role.role_name}-{self.Name}"
    
class Departments(models.Model):
    """Department name and member count."""
    dept_name=models.CharField(max_length=50,unique=True,null=False)
    count=models.SmallIntegerField(default=0)
    
    @classmethod
    def add_department(cls,dept_name:str):
        obj=cls.objects.create(dept_name=dept_name)
        return obj 
    
    class Meta:
        db_table= 'team_management"."Departments'
        verbose_name_plural = "departments"
        # ordering=["dept_name"]
    ...

class Functions(models.Model):
    """Employee function (e.g. role type); can be many per profile via ProfileFunction."""
    function=models.CharField(max_length=10,unique=True,null=False,verbose_name="employee-function")
    class Meta:
        db_table= 'team_management"."Functions'
        verbose_name_plural = "Functions"
    ...


# =============================================================================
# Leave management (tables in team_management schema)
# =============================================================================

class LeaveTypes(models.Model):
    """Leave type: full_day or half_day; referenced by leave applications."""
    id = models.AutoField(primary_key=True, auto_created=True)
    name = models.CharField(max_length=20, unique=True, null=False)

    class Meta:
        db_table = 'team_management"."leave_types'
        verbose_name = "leave type"
        verbose_name_plural = "leave types"

    def __str__(self):
        return self.name


class LeaveSummary(models.Model):
    """Per-user leave summary: total, used, emergency quota (from total), and computed remaining leaves."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="leave_summary",
        primary_key=True,
        db_column="user_id",
        to_field="username",
    )
    total_leaves = models.PositiveIntegerField(default=0)
    used_leaves = models.PositiveIntegerField(default=0)
    # Emergency leave quota: 10%% of total_leaves, filled on create and decremented when emergency leave is taken.
    emergency_leaves = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'team_management"."leave_summary'
        verbose_name = "leave summary"
        verbose_name_plural = "leave summaries"

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.emergency_leaves = self.total_leaves // 10
        super().save(*args, **kwargs)

    @property
    def remaining_leaves(self):
        """Calculated as (total_leaves - used_leaves)."""
        return max(0, self.total_leaves - self.used_leaves)

    def __str__(self):
        return f"{self.user.username} (remaining: {self.remaining_leaves})"


class LeaveStatus(models.Model):
    """Status of a leave application: Approved, Pending, or Rejected."""
    id = models.AutoField(primary_key=True, auto_created=True)
    name = models.CharField(max_length=20, unique=True, null=False)

    class Meta:
        db_table = 'team_management"."leave_status'
        verbose_name = "leave status"
        verbose_name_plural = "leave statuses"

    def __str__(self):
        return self.name


def _get_pending_leave_status_id():
    """Return the pk of the 'Pending' LeaveStatus (used as default for MD_approval)."""
    return LeaveStatus.objects.get(name="Pending").pk


class LeaveApplicationData(models.Model):
    """Single leave application with dates, type, reason, and approval chain (team lead, HR, MD, admin)."""
    class HalfDaySlot(models.TextChoices):
        FIRST_HALF = "First_Half", "First_Half"
        SECOND_HALF = "Second_Half", "Second_Half"

    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="leave_applications",
        db_column="applicant_id",
    )
    team_lead = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_applications_as_teamlead",
        db_column="team_lead_id",
    )
    start_date = models.DateField()
    duration_of_days = models.SmallIntegerField()
    leave_subject = models.CharField(max_length=255)
    reason = models.TextField()
    leave_type = models.ForeignKey(
        LeaveTypes,
        on_delete=models.PROTECT,
        related_name="leave_applications",
        db_column="leave_type_id",
    )
    half_day_slots = models.CharField(
        max_length=20,
        choices=HalfDaySlot.choices,
        null=True,
        blank=True,
    )
    team_lead_approval = models.ForeignKey(
        LeaveStatus,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        db_column="team_lead_approval_id",
    )
    HR_approval = models.ForeignKey(
        LeaveStatus,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        db_column="hr_approval_id",
    )
    MD_approval = models.ForeignKey(
        LeaveStatus,
        on_delete=models.PROTECT,
        related_name="+",
        default=_get_pending_leave_status_id,
        db_column="md_approval_id",
    )
    admin_approval = models.ForeignKey(
        LeaveStatus,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        db_column="admin_approval_id",
    )
    is_emergency = models.BooleanField(default=False)
    application_date = models.DateField(auto_now_add=True)
    approved_by_MD_at = models.DateTimeField(null=True, blank=True)
    note=models.TextField(null=True,blank=True)

    class Meta:
        db_table = 'team_management"."leave_application_data'
        verbose_name = "leave application"
        verbose_name_plural = "leave applications"

    def __str__(self):
        return f"leave {self.id}"



