from ems.urlImports import *
from .views import *

group_management_url=[path("createGroup/",create_group,name="groups_management"),
                      path("showCreatedGroups/",show_created_groups,name="groups_management"),
                      path("showGroupMembers/<int:group_id>/",get_group_members,name="groups_management"),
                      path("deleteGroup/<int:group_id>/",delete_group,name="groups_management"),
                      path("postMessages/<int:chat_id>/",delete_group,name="groups_management"),
                      path("getMessages/<int:chat_id>/",delete_group,name="groups_management"),
                      path("loadChats/",load_groups_and_chats,name="groups_management"),]
urlpatterns = []
urlpatterns+=group_management_url
