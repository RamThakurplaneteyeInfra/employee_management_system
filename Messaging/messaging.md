1. # Create Group

URL-{{BASE URL}}/messaging/createGroup/

response-

{"Message": "Group created successfully"}





# 2\. Show Group Members

URL-{{BASE URL}}/messaging/showGroupMembers/<[slug:group\_id](slug:group\\_id)>/

path parameter- group\_id (string)

response-

\[

    {

        "participant": "0001",

        "groupchat": "G04321",

        "participant\_name": "Jadhav"

    },

    {

        "participant": "20011",

        "groupchat": "G04321",

        "participant\_name": "tejraj D"

    }

]



# 3\. Show Created Groups

URL-{{BASE URL}}/messaging/showCreatedGroups/

response-

\[

    {

        "group\_id": "G65890",

        "name": "Not a group",

        "description": "here, I am testing the group-api",

        "created\_at": "27/01/26-13:29"

    },

    {

        "group\_id": "G04321",

        "name": "dummy",

        "description": "this is a dummy group",

        "created\_at": "27/01/26-12:43"

    }

]



# 4\. Add User to a Group

URL-{{BASE URL}}/messaging/addUser/<[slug:group\_id](slug:group\\_id)>/

path\_parameter-group\_id

response-

1. If new user: {"Message": "user added Successfully"}
2. If user already exist:{"Message": "user Already Exists"}



# 5.Delete User

URL-{{BASE URL}}/messaging/deleteUser/<[slug:group\_id](slug:group\\_id)>/<[slug:user\_id](slug:user\\_id)>/

path\_parameter- group\_id, user\_id

response-

1. If user is self group owner-{"Message": "self deletion is prohibited"}
2. If user exists and number of participants are lesser than 2: {"message": "there should be at least 2 members in the group"}
3. If user exists and number of participants are greater than 2:{"Message": "user deleted Successfully"}
4. If user doesn't exists-{"Message": "selected user is not a group member"}



# 6\. Load Groups and Chats

URL-{{BASE URL}}/messaging/loadChats/

response-

{

    "Group\_info": \[

        {

            "group\_id": "G04321",

            "group\_name": "dummy",

            "description": "this is a dummy group"

        },

        {

            "group\_id": "G65890",

            "group\_name": "Not a group",

            "description": "here, I am testing the group-api"

        }

    ],

    "chats\_info": \[

        {

            "chat\_id": "C11058574",

            "with": "tejraj D"

        },

        {

            "chat\_id": "C18252874",

            "with": "tushar sir"

        }

    ]

}



# 7\. Initiate Individual Chats

URL-{{BASE URL}}/messaging/startChat/

response-

1. When there is no prior chats with the choosen user-{"chat\_id": "C18252874", "participant": "tushar sir", "messages": {}}

2.When the chat already exists-

\[

    {

        "sender": "Jadhav",

        "message": "Hey, how are you doing?",

        "date": "27/01/26",

        "time": "15:08"

    }

]



# 8\. Post Message

URL-{{BASE URL}}/messaging/postMessages/<[slug:chat\_id](slug:chat\\_id)>/

path\_parameter-chat\_id(string)

response-

1. If the chat\_id is valid-{"message": "IndividualChats matching query does not exist."}
2. else:{"message": "Message sent successfully"}



# 9\. Get Message

URL-{{BASE URL}}/messaging/getMessages/<[slug:chat\_id](slug:chat\\_id)>/

path\_parameter-chat\_id(string)

response-

\[

    {

        "sender": "Jadhav",

        "message": "Hey, how do you doing?",

        "date": "27/01/26",

        "time": "12:58"

    },

    {

        "sender": "Jadhav",

        "message": "lets see what happen",

        "date": "27/01/26",

        "time": "12:48"

    },

    {

        "sender": "Jadhav",

        "message": "this is my first msg in this group.",

        "date": "27/01/26",

        "time": "12:46"

    }

]

