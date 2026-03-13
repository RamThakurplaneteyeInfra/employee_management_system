from ems.urlImports import *
from .views import *

group_management_url=[path("createGroup/",create_group,name="groups_management"),
                      path("showCreatedGroups/",show_created_groups,name="groups_management"),
                      path("showGroupMembers/<slug:group_id>/",api_to_get_group_members,name="groups_management"),
                      path("deleteUser/<slug:group_id>/<slug:user_id>/",delete_user,name="groups_management"),
                      path("addUser/<slug:group_id>/",add_user,name="groups_management"),
                      path("deleteGroup/<slug:group_id>/",delete_group,name="groups_management"),
                      path("postMessages/<slug:chat_id>/",post_message,name="groups_management"),
                      path("getMessages/<slug:chat_id>/",get_chats,name="groups_management"),
                      path("markSeen/<slug:chat_id>/",mark_seen,name="messaging_mark_seen"),
                      path("uploadFile/",upload_message_file,name="messaging_upload_file"),
                      path("addLink/",add_link,name="messaging_add_link"),
                      path("attachments/<int:attachment_id>/",delete_attachment,name="messaging_delete_attachment"),
                      path("files/<int:attachment_id>/url/",get_attachment_url,name="messaging_attachment_url"),
                      path("startChat/",access_or_create_conversation,name="groups_management"),                     
                      path("loadChats/",load_groups_and_chats,name="groups_management"),]
urlpatterns = []
urlpatterns += group_management_url
# Call APIs (Calling app): same /messaging/ prefix so frontend can use /messaging/initiateCall/ etc.
from Calling.urls import urlpatterns as calling_urlpatterns
urlpatterns += calling_urlpatterns
