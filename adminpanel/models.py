"""
Admin panel models: AssetType, Asset, BillCategory, Bill, ExpenseTracker, Vendor,
ExpenseCategory, ExpenseMonthlyAdvance.
API: {{baseurl}}/adminapi/ (asset-types, assets, billCategory, bills, expenses,
expense-categories, expense-advances, vendors, dashboard).
"""
import os
import uuid

from django.core.validators import FileExtensionValidator
from django.db import models
from task_management.models import TaskStatus

# Shared allow-list for vendor/bill uploads (extension only; size checked in serializers).
_DOCUMENT_ATTACHMENT_EXTENSIONS = (
    "pdf",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "txt",
)


def vendor_attachment_upload_to(instance, filename):
    """Store under MEDIA_ROOT with a random name; keep extension only (validated elsewhere)."""
    ext = os.path.splitext(filename)[1].lower()
    return f"vendor_attachments/{uuid.uuid4().hex}{ext}"


def bill_attachment_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"bill_attachments/{uuid.uuid4().hex}{ext}"


def expense_attachment_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"expense_attachments/{uuid.uuid4().hex}{ext}"


# 1️⃣ AssetType table (Hardware, Software)
class AssetType(models.Model):
    """Asset category (e.g. Hardware, Software); used by Asset."""
    name = models.CharField(max_length=100,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table= 'adminpanel"."Assettype'
        verbose_name_plural = "Assettypes"

    def __str__(self):
        return self.name

# 2️⃣ Asset table
class Asset(models.Model):
    """Asset record: type, name, author, code, and status (FK to TaskStatus)."""
    status = models.ForeignKey(TaskStatus,db_column="current_status",null=True,on_delete=models.CASCADE,serialize=True)
    asset_type = models.ForeignKey(AssetType, on_delete=models.CASCADE)
    asset_name = models.CharField(max_length=200)
    author = models.CharField(max_length=100)  # simple for now
    asset_code = models.CharField(max_length=50, unique=True, blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table= 'adminpanel"."Asset'
        verbose_name_plural = "Assets"
        ordering=["-created_at"]

    def __str__(self):
        return self.asset_name
    
#  Bill Category (Dropdown)
# This class represents a bill category in a Python Django model.
class BillCategory(models.Model):
    """Bill category for grouping bills."""
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table= 'adminpanel"."Billcategory'
        verbose_name_plural = "Billcategories"
        ordering=["-created_at"]

    def __str__(self):
        return self.name

class BillFloor(models.TextChoices):
    """Building floor(s) this bill applies to (API values: 3rd, 4th, both)."""

    THIRD = "3rd", "3rd floor"
    FOURTH = "4th", "4th floor"
    BOTH = "both", "Both floors"


# Bills
class Bill(models.Model):
    """Bill: category, amount, date, recipient, status, optional floor and attachment."""
    status = models.ForeignKey(TaskStatus,db_column="current_status",null=True,on_delete=models.CASCADE,serialize=True)
    category = models.ForeignKey(BillCategory, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date=models.DateField(auto_now_add=False,auto_now=False,default=None,null=True)
    recipient = models.CharField(max_length=200)
    floor = models.CharField(
        max_length=10,
        choices=BillFloor.choices,
        null=True,
        blank=True,
        help_text="3rd floor, 4th floor, or both (optional for legacy rows).",
    )
    attachment = models.FileField(
        upload_to=bill_attachment_upload_to,
        max_length=255,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=_DOCUMENT_ATTACHMENT_EXTENSIONS),
        ],
        help_text="Optional scan or invoice (PDF, image, Office). Max size enforced in API.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table= 'adminpanel"."Bill'
        verbose_name_plural = "Bills"
        ordering=["-created_at"]

    def __str__(self):
        return f"{self.category.name} - {self.amount}"


class ExpenseCategory(models.Model):
    """Expense line-item category (dropdown); admins can add more via API."""

    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'adminpanel"."Expensecategory'
        verbose_name_plural = "Expense categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ExpenseMonthlyAdvance(models.Model):
    """Opening advance for a calendar month; remaining = advance − sum(expenses in that month)."""

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()  # 1–12
    advance_amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'adminpanel"."ExpenseMonthlyAdvance'
        verbose_name_plural = "Expense monthly advances"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="uniq_expense_advance_year_month"),
        ]

    def __str__(self):
        return f"{self.year}-{self.month:02d}: {self.advance_amount}"


# ExpenseTracker
class ExpenseTracker(models.Model):
    """Expense record: title, amount, note, paid date, status, optional category and attachment."""
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True)
    status = models.ForeignKey(TaskStatus,serialize=True,db_column="current_status",null=True,on_delete=models.CASCADE)
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    attachment = models.FileField(
        upload_to=expense_attachment_upload_to,
        max_length=255,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=_DOCUMENT_ATTACHMENT_EXTENSIONS),
        ],
        help_text="Optional receipt or document (same types as bills/vendors). Max size enforced in API.",
    )
    paid_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table= 'adminpanel"."Expenses'
        verbose_name_plural = "Expenses"
        ordering=["-created_at"]
        
    def __str__(self):
        return self.title
    
# Vendor
class Vendor(models.Model):
    """Vendor: business name, GST, address, email, phones, optional service text and attachment."""
    business_name = models.CharField(max_length=200)
    gst_number = models.CharField(max_length=50, unique=True)
    office_address = models.TextField()
    email = models.EmailField()
    primary_phone = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True,null=True)
    service = models.TextField(
        blank=True,
        default="",
        help_text="Optional description of services offered.",
    )
    attachment = models.FileField(
        upload_to=vendor_attachment_upload_to,
        max_length=255,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=_DOCUMENT_ATTACHMENT_EXTENSIONS),
        ],
        help_text="Optional document (e.g. PDF, image, Office). Max size enforced in API.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table= 'adminpanel"."Vendor'
        verbose_name_plural = "Vendors"
        ordering=["-created_at"]

    def __str__(self):
        return self.business_name