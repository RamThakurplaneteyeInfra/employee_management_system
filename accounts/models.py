"""
Accounts app models: roles, branches, designations, departments, functions, profile, leave.
Used by accounts views and leave-applications; Profile linked via OneToOne to User.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import validate_email, MinValueValidator, MaxValueValidator
from datetime import timedelta
from decimal import Decimal


# A model for "Roles" table
class Roles(models.Model):
    """User role (e.g. Admin, MD, HR); used for permissions and dropdowns."""
    role_id=models.AutoField(primary_key=True,auto_created=True)
    role_name=models.CharField(max_length=20,unique=True,null=True)
    total_count=models.IntegerField(default=0,null=False,verbose_name="count")
    class Meta:
        db_table='team_management"."roles'
        verbose_name="role"
        verbose_name_plural="roles"
        
# A model for "Branches" table
class Branch(models.Model):
    """Office/branch location; used in Profile and dropdowns (getBranch)."""
    branch_id=models.SmallAutoField(primary_key=True,auto_created=True,verbose_name="id",editable=False)
    branch_name=models.CharField(max_length=25,unique=True,null=True,verbose_name="branch")
    class Meta:
        db_table='team_management"."Branches'
        verbose_name="branch"
        verbose_name_plural="branches"
        
# # A model for "Designations" table
class Designation(models.Model):
    """Job designation/title; used in Profile and getDesignations dropdown."""
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
    is_logged_in = models.BooleanField(default=False, help_text="True when user is logged in, False when logged out.")
    gender = models.CharField(max_length=20, null=True, blank=True, verbose_name="gender", db_column="gender", choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")])
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
    # Per-employee casual/earn balances; Decimal so half-day values (e.g. 1.5, 4.5) are supported.
    # MinValueValidator(0) preserves the non-negative semantics that the previous PositiveIntegerField had.
    casual_leaves = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    earn_leaves = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    # Menstrual leave for female employees only. Always 0 or 1; reset to 1 on the
    # 1st of every month by the `credit_menstrual_leave` management command, and
    # consumed (set to 0) when an approved Menstrual leave application is processed.
    # Does not carry over month-to-month and does not affect used_leaves.
    menstrual_leaves = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(1)],
    )
    # Cumulative unpaid leave days taken (overflow when both casual_leaves and
    # earn_leaves are exhausted at approval time). Decimal so half-day overflow
    # is supported.
    unpaid_leaves = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    # Bookkeeping for the auto-credit jobs (`credit_earn_leave`,
    # `credit_casual_leave`). Each command stamps `today` on success so a
    # second run inside the same month / quarter is a no-op (idempotent).
    # Nullable so existing rows pre-feature don't break; seeded to today by
    # the migration that introduces these columns.
    last_earn_credit_on = models.DateField(null=True, blank=True)
    last_casual_credit_on = models.DateField(null=True, blank=True)
    # Monthly short-leave quota (`settings.SHORT_LEAVE_MONTHLY_QUOTA`).
    # at calendar month rollover (lazy on use / GET summary / `credit_short_leave_monthly`).
    short_leaves_remaining = models.PositiveSmallIntegerField(default=2)
    # First day of the calendar month for which `short_leaves_remaining` was last refreshed.
    short_leave_credit_month_first = models.DateField(null=True, blank=True)

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
    alternative = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_applications_as_alternative",
        db_column="alternative_id",
    )
    start_date = models.DateField()
    # Decimal so half-day values (e.g. 0.5, 1.5) are accepted without truncation.
    # Existing integer rows are read back unchanged (1 -> Decimal('1.0')).
    duration_of_days = models.DecimalField(max_digits=5, decimal_places=1)
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
        null=True,
        blank=True,
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
    # Cover person accepts/rejects covering for the applicant (parallel to TL/HR/MD rails).
    alternative_approval = models.ForeignKey(
        LeaveStatus,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        db_column="alternative_approval_id",
    )
    alternative_responded_at = models.DateTimeField(null=True, blank=True)
    is_emergency = models.BooleanField(default=False)
    application_date = models.DateField(auto_now_add=True)
    approved_by_MD_at = models.DateTimeField(null=True, blank=True)
    note=models.TextField(null=True,blank=True)
    # Per-application split filled at MD-approval time (waterfall casual -> earn -> unpaid).
    # All zeros for legacy / unapproved / Menstrual / Emergency rows.
    casual_used = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0"))
    earn_used = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0"))
    unpaid_used = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0"))
    # True after this row consumed one monthly short-leave slot (idempotent debit).
    short_leave_slot_consumed = models.BooleanField(default=False)
    # Two-hour short leave: wall-clock start within configured office hours (leave_type = Short Leave).
    short_leave_start_time = models.TimeField(null=True, blank=True)

    class Meta:
        db_table = 'team_management"."leave_application_data'
        verbose_name = "leave application"
        verbose_name_plural = "leave applications"

    def __str__(self):
        return f"leave {self.id}"



