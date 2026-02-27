from ems.urlImports import *
from .views import *
urlpatterns = [
    
                path("callableUsers/",get_callable_users,name="callable_users"),
                path("initiateCall/",initiate_call,name="initiate_call"),
                path("acceptCall/",accept_call,name="accept_call"),
                path("declineCall/",decline_call,name="decline_call"),
                path("endCall/",end_call,name="end_call"),
                path("pendingCalls/",get_pending_calls,name="pending_calls"),
                path("activeCalls/",get_active_calls,name="active_calls"),
                path("endAllMyCalls/",end_all_my_calls,name="end_all_my_calls"),
                path("initiateGroupCall/", initiate_group_call, name="initiate_group_call"),
                path("joinGroupCall/", join_group_call, name="join_group_call"),
                path("leaveGroupCall/", leave_group_call, name="leave_group_call"),
                path("endGroupCall/", end_group_call, name="end_group_call"),
                path("activeGroupCalls/", get_active_group_calls, name="active_group_calls"),]