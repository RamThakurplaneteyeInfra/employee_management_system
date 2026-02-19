from rest_framework import viewsets
from rest_framework.decorators import api_view
from django.db.models import Count, Sum
from rest_framework.decorators import permission_classes
from .permissions import AdminPermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import AssetType, Asset, BillCategory, Bill, ExpenseTracker, Vendor
# # # # # #  baseurl="http://localhost:8000"  # # # # # # # # # # # #
# Base path: {{baseurl}}/adminapi/

from .serializers import (
    AssetTypeSerializer, 
    AssetSerializer,
    BillCategorySerializer,
    BillSerializer,
    ExpenseTrackerSerializer,
    VendorSerializer,    
    )

# Note: DRF ViewSets do not support async methods - they don't await coroutines.
# Sync views work under ASGI; Django runs them in a thread pool automatically.


# ==================== AssetTypeViewSet ====================
# URL: {{baseurl}}/adminapi/asset-types/  | CRUD
class AssetTypeViewSet(viewsets.ModelViewSet):
    queryset = AssetType.objects.all()
    serializer_class = AssetTypeSerializer
    permission_classes = [IsAuthenticated,AdminPermission]


# ==================== AssetViewSet ====================
# URL: {{baseurl}}/adminapi/assets/  | CRUD
class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related("asset_type", "status")
    serializer_class = AssetSerializer
    permission_classes = [AdminPermission]


# ==================== BillCategoryViewSet ====================
# URL: {{baseurl}}/adminapi/billCategory/  | CRUD
class BillCategoryViewSet(viewsets.ModelViewSet):
    queryset = BillCategory.objects.filter()
    serializer_class = BillCategorySerializer
    permission_classes = [AdminPermission]


# ==================== BillViewSet ====================
# URL: {{baseurl}}/adminapi/bills/  | CRUD
class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.select_related("category", "status")
    serializer_class = BillSerializer
    permission_classes = [AdminPermission]


# ==================== ExpenseTrackerViewSet ====================
# URL: {{baseurl}}/adminapi/expenses/  | CRUD
class ExpenseTrackerViewSet(viewsets.ModelViewSet):
    queryset = ExpenseTracker.objects.select_related("status")
    serializer_class = ExpenseTrackerSerializer
    permission_classes = [AdminPermission]


# ==================== VendorViewSet ====================
# URL: {{baseurl}}/adminapi/vendors/  | CRUD
class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [AdminPermission]


# ==================== dashboard_summary ====================
# Dashboard summary (assets, bills, expenses, vendors).
# URL: {{baseurl}}/adminapi/dashboard/
# Method: GET

@api_view(['GET'])
@permission_classes([AdminPermission])
def dashboard_summary(request):
    """Sync view - DRF's @api_view doesn't properly await async functions."""
    assets_total = Asset.objects.count()
    assets_by_type = Asset.objects.values('asset_type__name').annotate(count=Count('id'))
    bills_total = Bill.objects.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
    bills_by_category = Bill.objects.values('category__name').annotate(total=Sum('amount'))
    expenses_total = ExpenseTracker.objects.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
    vendors_total = Vendor.objects.count()
    data = {
        "assets": {"total": assets_total, "by_type": list(assets_by_type)},
        "bills": {"total_amount": bills_total, "by_category": list(bills_by_category)},
        "expense_tracker": {"total_amount": expenses_total},
        "vendors": {"total": vendors_total},
    }
    return Response(data)