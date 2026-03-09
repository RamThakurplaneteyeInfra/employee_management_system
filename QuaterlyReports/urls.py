from django.urls import path
from .views import *
urlpatterns = [
    path("getMonthlySchedule/", get_meeting_head_and_subhead),
    path("addDayEntries/",create_multiple_user_entries),
    path("getUserEntries/",get_entries),
    path("changeStatus/<int:user_entry_id>/",change_status),
    path("deleteEntry/<int:user_entry_id>/",delete_entry),
    path("addMeetingHeadSubhead/",add_meeting_head_subhead),
    path("get_functions_and_actionable_goals/",get_functions_and_actionable_goals),
    path("ActionableEntries/", entry_list_create),
    path("ActionableEntriesByID/<int:id>/", entry_detail_update_delete),
    path("ActionableEntriesByID/<int:id>/share/", share_further),
    # Co-author: list entries and get/update (including approval) where current user is co_author
    path("ActionableEntriesCoAuthor/", co_author_entries_list),
    path("ActionableEntriesCoAuthor/<int:id>/", co_author_entry_detail),
    # Shared-with: list and get/update entries where current user is share_with (same fields; only approved entries)
    path("ActionableEntriesSharedWith/", shared_with_entries_list),
    path("ActionableEntriesSharedWith/<int:id>/", shared_with_entry_detail),
]
