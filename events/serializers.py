from rest_framework import serializers
from django.db.models import Q
from .models import *
from ems.RequiredImports import *
from accounts.filters import _get_users_Name_sync
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
        queryset=User.objects.all(),write_only=True,required=True)
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
        
    def get_member_details(self, obj: BookSlot):
        # Use prefetched slotmembers (no extra query per slot).
        return [
            {
                "full_name": (
                    getattr(m.member.accounts_profile, "Name", None)
                    or _get_users_Name_sync(m.member)
                )
            }
            for m in obj.slotmembers.all()
        ]

    def get_creater_details(self, obj: BookSlot):
        # Use prefetched created_by__accounts_profile when available.
        if obj.created_by_id is None:
            return {"full_name": None}
        profile = getattr(obj.created_by, "accounts_profile", None)
        name = getattr(profile, "Name", None) if profile else None
        return {"full_name": name or _get_users_Name_sync(obj.created_by)}

    def _get_overlapping_slots(self, date_val, start_time, end_time, exclude_slot_id=None):
        """Slots on the same date whose time range overlaps (start_time, end_time)."""
        qs = BookSlot.objects.filter(
            date=date_val
        ).filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        )
        if exclude_slot_id is not None:
            qs = qs.exclude(pk=exclude_slot_id)
        return qs

    def validate(self, attrs):
        date_val = attrs.get("date")
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
        room = attrs.get("room")
        members = attrs.get("members", [])

        if date_val is None or start_time is None or end_time is None:
            return attrs

        if start_time >= end_time:
            raise serializers.ValidationError(
                "end_time must be after start_time."
            )
        if not members:
            raise serializers.ValidationError(
                "There should be at least one member in the slot."
            )

        exclude_slot_id = self.instance.pk if self.instance else None
        overlapping = self._get_overlapping_slots(
            date_val, start_time, end_time, exclude_slot_id=exclude_slot_id
        )

        total_rooms = Room.objects.filter(is_active=True).count()
        if total_rooms == 0:
            raise serializers.ValidationError("No rooms are available for booking.")

        rooms_booked_in_period = overlapping.values_list("room_id", flat=True).distinct()
        rooms_booked_count = len(set(rooms_booked_in_period))
        if rooms_booked_count >= total_rooms:
            raise serializers.ValidationError(
                "No room empty for booking the slot."
            )

        if overlapping.filter(room=room).exists():
            raise serializers.ValidationError(
                "This room is already booked for the selected time slot."
            )

        request = self.context.get("request")
        if request and request.user:
            creator = request.user
            if overlapping.filter(created_by=creator).exists():
                raise serializers.ValidationError(
                    "You already have a slot in this time frame."
                )

        for member in members:
            if overlapping.filter(created_by=member).exists():
                raise serializers.ValidationError(
                    {"members": f"User {member.username} already has a slot in this time frame."}
                )
            if SlotMembers.objects.filter(slot__in=overlapping, member=member).exists():
                raise serializers.ValidationError(
                    {"members": f"User {member.username} already has a slot in this time frame."}
                )

        return attrs

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
        # Use prefetched tourmembers to avoid N+1.
        return [
            {
                "username": tm.member.username,
                "full_name": (
                    getattr(tm.member.accounts_profile, "Name", None)
                    or _get_users_Name_sync(tm.member)
                ),
            }
            for tm in obj.tourmembers.all()
        ]

    def get_creater_details(self, obj):
        profile = getattr(obj.created_by, "accounts_profile", None)
        name = getattr(profile, "Name", None) if profile else None
        return {"full_name": name or _get_users_Name_sync(obj.created_by)}

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
    # schedule_time = serializers.SerializerMethodField()
    class Meta:
        model = Meeting
        fields = [
            'id', 'users', 'user_details', 'meeting_type', 
            'time', 'meeting_room', 'is_active',"created_at"
        ]

    def get_user_details(self, obj):
        return [
            {
                "username": user.username,
                "full_name": (
                    getattr(user.accounts_profile, "Name", None)
                    or _get_users_Name_sync(user)
                ),
            }
            for user in obj.users.all()
        ]
        
    # def get_schedule_time(self,obj:Meeting):
    #     schedule_time=obj.created_at+timedelta(minutes=obj.time)
    #     return schedule_time.strftime("%d/%m/%Y, %H:%M:%S")
        
        