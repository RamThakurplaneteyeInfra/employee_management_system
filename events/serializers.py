from rest_framework import serializers
from .models import *
from ems.RequiredImports import *
from accounts.filters import get_users_Name
class SlotMemberSerializer(serializers.ModelSerializer):
    member=serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="username")
    class Meta:
        model = SlotMembers
        fields = ['member']
        
class BookSlotSerializer(serializers.ModelSerializer):
    status= serializers.SlugRelatedField(
        queryset=BookingStatus.objects.all(),
        slug_field="status_name"
    )
    room= serializers.SlugRelatedField(
        queryset=Room.objects.all(),
        slug_field="name")
    
    members = serializers.SlugRelatedField(
        many=True,
        slug_field='username',
        queryset=User.objects.all(),write_only=True)
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    member_details = serializers.SerializerMethodField()
    creater_details = serializers.SerializerMethodField()
    class Meta:
        model = BookSlot
        fields = [
            'id', 'meeting_title', 'date', 'start_time', 'end_time', 
            'room', 'description', 'meeting_type', 'status',"members",
            'created_at','member_details',"creater_details","created_by"
        ]
        
    def get_member_details(self, obj):
        # Accesses the ManyToMany relationship
        return [
            {
                "username": user.username,
                "full_name": get_users_Name(user) # fallback if name is empty
            } 
            for user in obj.members.all()]
        
    def get_creater_details(self, obj):
        return {
                "full_name": get_users_Name(obj.created_by) # fallback if name is empty
            }
        
    def create(self, validated_data):
        # Extract the list of user objects identified by username
        member_users = validated_data.pop('members', [])
        # print(validated_data)
        # Create the BookSlot instance
        book_slot = BookSlot.objects.create(**validated_data)
        # Manually create entries in the through table
        for user in member_users:
            SlotMembers.objects.create(slot=book_slot, member=user)
        return book_slot

    def update(self, instance, validated_data):
        member_users = validated_data.pop('members', None)
        
        # Standard update for BookSlot fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        # print(member_users)
        # If members were provided in the request, replace the old ones
        if member_users is not None:
            SlotMembers.objects.filter(slot=instance).delete()
            for user in member_users:
                # print(user)
                SlotMembers.objects.create(slot=instance, member=user)
        return instance
class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "name"]

class BookingStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingStatus
        fields = ["status_name"]

class TourMembersSerializer(serializers.ModelSerializer):
    member=serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="username")
    class Meta:
        model = tourmembers
        fields = ['member']

class TourSerializer(serializers.ModelSerializer):
    members = serializers.SlugRelatedField(
        many=True,
        slug_field='username',
        queryset=User.objects.all()
    )
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    member_details = serializers.SerializerMethodField()
    creater_details = serializers.SerializerMethodField()
    class Meta:
        model = Tour
        fields = [
            'id', 'tour_name', 'starting_date','description','created_at',"location",'member_details',"creater_details","total_members","duration_days","created_by","members",
        ]
        
    def get_member_details(self, obj):
        # Accesses the ManyToMany relationship
        return [
            {
                "username": user.username,
                "full_name": get_users_Name(user) # fallback if name is empty
            } 
            for user in obj.members.all()]
        
    def get_creater_details(self, obj):
        return {
                "full_name": get_users_Name(obj.created_by) # fallback if name is empty
            }

    def create(self, validated_data):
        # Extract the list of user objects identified by username
        member_users = validated_data.pop('members', [])
        print(validated_data)
        # Create the BookSlot instance
        tour = Tour.objects.create(**validated_data)
        # Manually create entries in the through table
        count=0
        for user in member_users:
            tourmembers.objects.create(tour=tour, member=user)
            count+=1
        
        setattr(tour,"total_members",count)
        tour.save()
        return tour

    def update(self, instance:Tour, validated_data):
        member_users = validated_data.pop('members', None)
        
        # Standard update for BookSlot fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If members were provided in the request, replace the old ones
        if member_users is not None:
            tourmembers.objects.filter(tour=instance).delete()
            instance.total_members=0
            instance.save()
            count=0
            for user in member_users:
                tourmembers.objects.create(tour=instance, member=user)
                count+=1
            setattr(instance,"total_members",count)
            instance.save()
        return instance

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = '__all__'

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
        
class MeetingSerializer(serializers.ModelSerializer):
    # For WRITE: Accept a list of usernames
    users = serializers.SlugRelatedField(
        many=True,
        slug_field='username',
        queryset=User.objects.all()
    )
    is_active = serializers.BooleanField(default=True)
    meeting_room= serializers.SlugRelatedField(
        queryset=Room.objects.all(),
        slug_field="name")
    

    # For READ: Show detailed info (Username + Full Name)
    user_details = serializers.SerializerMethodField()
    schedule_time = serializers.SerializerMethodField()
    class Meta:
        model = Meeting
        fields = [
            'id', 'users', 'user_details', 'meeting_type', 
            'time', 'meeting_room', 'is_active',"schedule_time"
        ]

    def get_user_details(self, obj):
        return [
            {
                "username": user.username, 
                "full_name": get_users_Name(user)
            } for user in obj.users.all()
        ]
        
    def get_schedule_time(self,obj:Meeting):
        schedule_time=obj.created_at+timedelta(minutes=obj.time)
        return schedule_time.strftime("%d/%m/%Y, %H:%M:%S")
        
        