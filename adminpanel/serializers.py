from rest_framework import serializers
from task_management.models import TaskStatus
from .models import (
    AssetType, 
    Asset,
    BillCategory,
    Bill,
    ExpenseTracker,
    Vendor,
    )


# 1 AssetType Serializer (Dropdown)
class AssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetType
        fields = ['id', 'name']

# 2 Asset Serializer
class AssetSerializer(serializers.ModelSerializer):
    asset_code = serializers.ReadOnlyField()
    asset_type = serializers.SlugRelatedField(
        queryset=AssetType.objects.all(),
        slug_field="name"
    )
    status= serializers.SlugRelatedField(
        queryset=TaskStatus.objects.all(),
        slug_field="status_name")

    class Meta:
        model = Asset
        fields = [
            'id',
            'asset_type',
            'asset_name',
            'author',
            'asset_code',
            'created_at',
            'updated_at',
            'status'
        ]
        read_only_fields = ['asset_code', 'created_at', 'updated_at']
    
# 3 Bill Category
class BillCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BillCategory
        fields = ['id', 'name']


# 4 Bills
class BillSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        queryset=BillCategory.objects.all(),
        slug_field="name"
    )
    status = serializers.SlugRelatedField(
        queryset=TaskStatus.objects.all(),
        slug_field="status_name")
    
    class Meta:
        model = Bill
        fields = ['id', 'category', 'amount', 'recipient', 'created_at',"status"]
        read_only_fields = ['created_at']


# 5 Expense Tracker
class ExpenseTrackerSerializer(serializers.ModelSerializer):
    status = serializers.SlugRelatedField(
        queryset=TaskStatus.objects.all(),
        slug_field="status_name")
    class Meta:
        model = ExpenseTracker
        fields = ['id', 'title', 'amount', 'note', 'paid_date', 'created_at',"status"]
        read_only_fields = ['created_at']


# 6 Vendor
class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            'id',
            'business_name',
            'gst_number',
            'office_address',
            'email',
            'primary_phone',
            'alternate_phone',
            'created_at'
        ]
        read_only_fields = ['created_at']

