from django.db import models
from task_management.models import TaskStatus
# from task_management.filters import get_default_task_status

# 1️⃣ AssetType table (Hardware, Software)
class AssetType(models.Model):
    name = models.CharField(max_length=100,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table= 'adminpanel"."Assettype'
        verbose_name_plural = "Assettypes"

    def __str__(self):
        return self.name

# 2️⃣ Asset table
class Asset(models.Model):
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
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table= 'adminpanel"."Billcategory'
        verbose_name_plural = "Billcategories"
        ordering=["-created_at"]

    def __str__(self):
        return self.name

# Bills
class Bill(models.Model):
    status = models.ForeignKey(TaskStatus,db_column="current_status",null=True,on_delete=models.CASCADE,serialize=True)
    category = models.ForeignKey(BillCategory, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date=models.DateField(auto_now_add=False,auto_now=False,default=None,null=True)
    recipient = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table= 'adminpanel"."Bill'
        verbose_name_plural = "Bills"
        ordering=["-created_at"]

    def __str__(self):
        return f"{self.category.name} - {self.amount}"
    
# ExpenseTracker
class ExpenseTracker(models.Model):
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True)
    status = models.ForeignKey(TaskStatus,serialize=True,db_column="current_status",null=True,on_delete=models.CASCADE)
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
    business_name = models.CharField(max_length=200)
    gst_number = models.CharField(max_length=50, unique=True)
    office_address = models.TextField()
    email = models.EmailField()
    primary_phone = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table= 'adminpanel"."Vendor'
        verbose_name_plural = "Vendors"
        ordering=["-created_at"]

    def __str__(self):
        return self.business_name