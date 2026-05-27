from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Profile

from .models import FarmServiceRequest, FarmServiceTask


class EmployeeDropdownSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="Employee_id_id")
    name = serializers.CharField(source="Name")

    class Meta:
        model = Profile
        fields = ["id", "name"]


class FarmServiceTaskWriteSerializer(serializers.ModelSerializer):
    team_members = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = FarmServiceTask
        fields = ["task_name", "team_members", "status"]

    def validate_task_name(self, value):
        task = (value or "").strip()
        if not task:
            raise serializers.ValidationError("task_name cannot be blank.")
        return task

    def validate_team_members(self, value):
        usernames = []
        for item in value or []:
            raw = "" if item is None else str(item).strip()
            if raw:
                usernames.append(raw)
        unique_usernames = list(dict.fromkeys(usernames))
        users = list(User.objects.filter(username__in=unique_usernames))
        found = {u.username for u in users}
        missing = [u for u in unique_usernames if u not in found]
        if missing:
            raise serializers.ValidationError(
                f"Invalid team member id(s): {', '.join(missing)}"
            )
        return users


class FarmServiceTaskReadSerializer(serializers.ModelSerializer):
    team_members = serializers.SerializerMethodField()

    class Meta:
        model = FarmServiceTask
        fields = ["id", "task_name", "team_members", "status", "created_at", "updated_at"]

    def get_team_members(self, obj):
        members = obj.team_members.all().order_by("username")
        return [{"id": user.username, "name": user.get_full_name() or user.username} for user in members]


class FarmServiceRequestSerializer(serializers.ModelSerializer):
    tasks = serializers.ListField(write_only=True, required=False)
    created_by = serializers.SerializerMethodField(read_only=True)
    no_of_tasks = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FarmServiceRequest
        fields = [
            "id",
            "service_name",
            "created_by",
            "tasks",
            "no_of_tasks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "no_of_tasks", "created_at", "updated_at"]

    def validate_service_name(self, value):
        service = (value or "").strip()
        if not service:
            raise serializers.ValidationError("service_name cannot be blank.")
        return service

    def validate_tasks(self, value):
        if not value:
            raise serializers.ValidationError("At least one task is required.")
        if not isinstance(value, list):
            raise serializers.ValidationError("tasks must be a list.")
        row_serializer = FarmServiceTaskWriteSerializer(data=value, many=True)
        row_serializer.is_valid(raise_exception=True)
        return row_serializer.validated_data

    def validate(self, attrs):
        if self.instance is None and "tasks" not in attrs:
            raise serializers.ValidationError({"tasks": "At least one task is required."})
        return attrs

    def get_created_by(self, obj):
        user = obj.created_by
        return {"id": user.username, "name": user.get_full_name() or user.username}

    def get_no_of_tasks(self, obj):
        return obj.tasks.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tasks"] = FarmServiceTaskReadSerializer(instance.tasks.all(), many=True).data
        return data

    def create(self, validated_data):
        tasks_data = validated_data.pop("tasks", [])
        request = FarmServiceRequest.objects.create(**validated_data)
        for row in tasks_data:
            members = row.pop("team_members", [])
            task = FarmServiceTask.objects.create(request=request, **row)
            if members:
                task.team_members.set(members)
        return request

    def update(self, instance, validated_data):
        tasks_data = validated_data.pop("tasks", None)
        if "service_name" in validated_data:
            instance.service_name = validated_data["service_name"]
            instance.save(update_fields=["service_name", "updated_at"])

        if tasks_data is not None:
            # Explicit replace semantics for update: existing task rows are removed,
            # then recreated from payload to keep API behavior deterministic.
            instance.tasks.all().delete()
            for row in tasks_data:
                members = row.pop("team_members", [])
                task = FarmServiceTask.objects.create(request=instance, **row)
                if members:
                    task.team_members.set(members)
        return instance

