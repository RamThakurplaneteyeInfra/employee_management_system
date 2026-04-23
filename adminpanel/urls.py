from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssetTypeViewSet,
    AssetViewSet,
    BillCategoryViewSet,
    BillViewSet,
    ExpenseCategoryViewSet,
    ExpenseMonthlyAdvanceViewSet,
    ExpenseTrackerViewSet,
    VendorViewSet,
    dashboard_summary,
)

router = DefaultRouter()
router.register(r'asset-types', AssetTypeViewSet, basename='assettype')
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'billCategory', BillCategoryViewSet)
router.register(r'bills', BillViewSet)
router.register(r'expense-categories', ExpenseCategoryViewSet, basename='expensecategory')
router.register(r'expense-advances', ExpenseMonthlyAdvanceViewSet, basename='expenseadvance')
router.register(r'expenses', ExpenseTrackerViewSet)
router.register(r'vendors', VendorViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', dashboard_summary, name='dashboard-summary'),
]
