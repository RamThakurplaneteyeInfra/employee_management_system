from rest_framework import viewsets
from rest_framework.decorators import api_view
from django.db.models import Count,Sum
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import AssetType, Asset, BillCategory, Bill, ExpenseTracker, Vendor
from .serializers import (
    AssetTypeSerializer, 
    AssetSerializer,
    BillCategorySerializer,
    BillSerializer,
    ExpenseTrackerSerializer,
    VendorSerializer,    
    )

class AssetTypeViewSet(ModelViewSet):
    queryset = AssetType.objects.all()
    serializer_class = AssetTypeSerializer
    permission_classes = [AllowAny]  # 👈 allow all for testing


class AssetViewSet(ModelViewSet):
    queryset = Asset.objects.select_related("asset_type", "status")
    serializer_class = AssetSerializer
    permission_classes = [AllowAny]


class BillCategoryViewSet(viewsets.ModelViewSet):
    queryset = BillCategory.objects.filter()
    serializer_class = BillCategorySerializer
    permission_classes = [AllowAny]


class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.select_related("category", "status")
    serializer_class = BillSerializer
    permission_classes = [AllowAny]


class ExpenseTrackerViewSet(viewsets.ModelViewSet):
    queryset = ExpenseTracker.objects.select_related("status")
    serializer_class = ExpenseTrackerSerializer
    permission_classes = [AllowAny]


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [AllowAny]


# Dashboard API

@api_view(['GET'])
def dashboard_summary(request):
    # Assets summary
    assets_total = Asset.objects.count()
    assets_by_type = Asset.objects.values('asset_type__name').annotate(count=Count('id'))

    # Bills summary
    bills_total = Bill.objects.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
    bills_by_category = Bill.objects.values('category__name').annotate(total=Sum('amount'))

    # Expense Tracker summary
    expenses_total = ExpenseTracker.objects.aggregate(total_amount=Sum('amount'))['total_amount'] or 0

    # Vendors summary
    vendors_total = Vendor.objects.count()

    data = {
        "assets": {
            "total": assets_total,
            "by_type": list(assets_by_type)
        },
        "bills": {
            "total_amount": bills_total,
            "by_category": list(bills_by_category)
        },
        "expense_tracker": {
            "total_amount": expenses_total
        },
        "vendors": {
            "total": vendors_total
        }
    }

    return Response(data)