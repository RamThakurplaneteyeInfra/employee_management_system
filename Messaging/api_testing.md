# Messaging APIs – Testing reference

Base prefix: `{{baseurl}}/messaging/`

Use this file to document all executable Messaging APIs (group management, chats, attachments).

---

## 1. Group management

- `POST {{baseurl}}/messaging/createGroup/`
- `GET  {{baseurl}}/messaging/showCreatedGroups/`
- `GET  {{baseurl}}/messaging/showGroupMembers/<group_id>/`
- `DELETE {{baseurl}}/messaging/deleteUser/<group_id>/<user_id>/`
- `POST {{baseurl}}/messaging/addUser/<group_id>/`
- `DELETE {{baseurl}}/messaging/deleteGroup/<group_id>/`

> Document request/response bodies for each of the above here.

---

## 2. Group / individual chats

- `POST {{baseurl}}/messaging/postMessages/<chat_id>/`
- `GET  {{baseurl}}/messaging/getMessages/<chat_id>/`
- `POST {{baseurl}}/messaging/startChat/`
- `GET  {{baseurl}}/messaging/loadChats/`

> Describe payloads (message only, attachment only, message + attachment) and expected response format (`message`, `attachments`, `quote`) here.

---

## 3. Attachments

- `POST   {{baseurl}}/messaging/uploadFile/`
- `POST   {{baseurl}}/messaging/addLink/`
- `DELETE {{baseurl}}/messaging/attachments/<attachment_id>/`
- `GET    {{baseurl}}/messaging/files/<attachment_id>/url/`

> Add detailed examples for file upload, link add, delete, and pre-signed URL fetch here.

