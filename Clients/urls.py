"""
Client Lead API URLs.
Wire in ems/urls.py: path('clientsapi/', include('Clients.urls')),
"""
from django.urls import path
from . import views

urlpatterns = [
    path("products/", views.product_list, name="client_products"),
    path("employees/", views.employee_list, name="client_employees"),
    path("stages/", views.stage_list, name="client_stages"),
    path("profiles/", views.profile_list_create, name="client_profiles"),
    path("profiles/<int:profile_id>/", views.profile_detail_update_delete, name="client_profile_detail"),
    path("profiles/<int:profile_id>/members/", views.profile_members, name="client_profile_members"),
    path("profiles/<int:profile_id>/conversations/", views.conversation_list_create, name="client_conversations"),
    path("profiles/<int:profile_id>/conversations/<int:note_id>/", views.conversation_update_delete, name="client_conversation_detail"),
]
