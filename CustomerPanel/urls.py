from django.urls import path

from . import views


urlpatterns = [
    path("entries/", views.list_create_entries, name="customer_panel_list_create"),
    path("entries/<int:entry_id>/", views.detail_update_delete_entry, name="customer_panel_detail"),
    path("entries/<int:entry_id>/amount-logs/", views.amount_log_list_create, name="customer_panel_amount_log_list_create"),
    path(
        "entries/<int:entry_id>/amount-logs/<int:log_id>/",
        views.amount_log_detail_update_delete,
        name="customer_panel_amount_log_detail",
    ),
]

