from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from accounts.models import Profile

from .models import FarmServiceRequest, FarmServiceSubtask, FarmServiceTask


class EmployeeDropdownSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="Employee_id_id")
    name = serializers.CharField(source="Name")

    class Meta:
        model = Profile
        fields = ["id", "name"]


class FarmServiceTaskWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    task_name = serializers.CharField(required=False)
    status = serializers.BooleanField(required=False)
    team_members = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    subtasks = serializers.ListField(required=False, allow_empty=True)

    class Meta:
        model = FarmServiceTask
        fields = ["id", "task_name", "team_members", "status", "subtasks"]

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

    def validate_subtasks(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("subtasks must be a list.")
        row_serializer = FarmServiceSubtaskWriteSerializer(data=value, many=True)
        row_serializer.is_valid(raise_exception=True)
        return row_serializer.validated_data

    def validate(self, attrs):
        task_id = attrs.get("id")
        if not task_id and "task_name" not in attrs:
            raise serializers.ValidationError(
                {"task_name": "task_name is required for new task."}
            )
        return attrs


class FarmServiceSubtaskWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    subtask_name = serializers.CharField(required=False)
    status = serializers.BooleanField(required=False)
    assigned_member = serializers.CharField(required=False)

    class Meta:
        model = FarmServiceSubtask
        fields = ["id", "subtask_name", "assigned_member", "status"]

    def validate_subtask_name(self, value):
        subtask = (value or "").strip()
        if not subtask:
            raise serializers.ValidationError("subtask_name cannot be blank.")
        return subtask

    def validate_assigned_member(self, value):
        username = (value or "").strip()
        if not username:
            raise serializers.ValidationError("assigned_member cannot be blank.")
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError(
                f"Invalid assigned_member id: {username}"
            ) from exc

    def validate(self, attrs):
        subtask_id = attrs.get("id")
        if not subtask_id and "subtask_name" not in attrs:
            raise serializers.ValidationError(
                {"subtask_name": "subtask_name is required for new subtask."}
            )
        if not subtask_id and "assigned_member" not in attrs:
            raise serializers.ValidationError(
                {"assigned_member": "assigned_member is required for new subtask."}
            )
        return attrs


class FarmServiceSubtaskReadSerializer(serializers.ModelSerializer):
    assigned_member = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = FarmServiceSubtask
        fields = [
            "id",
            "subtask_name",
            "assigned_member",
            "created_by",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_assigned_member(self, obj):
        user = obj.assigned_member
        return {"id": user.username, "name": user.get_full_name() or user.username}

    def get_created_by(self, obj):
        user = obj.created_by
        return {"id": user.username, "name": user.get_full_name() or user.username}


class FarmServiceTaskReadSerializer(serializers.ModelSerializer):
    team_members = serializers.SerializerMethodField()
    subtasks = serializers.SerializerMethodField()

    class Meta:
        model = FarmServiceTask
        fields = [
            "id",
            "task_name",
            "team_members",
            "status",
            "subtasks",
            "created_at",
            "updated_at",
        ]

    def get_team_members(self, obj):
        members = obj.team_members.all().order_by("username")
        return [{"id": user.username, "name": user.get_full_name() or user.username} for user in members]

    def get_subtasks(self, obj):
        subtasks = obj.subtasks.all().order_by("id")
        return FarmServiceSubtaskReadSerializer(subtasks, many=True).data


class FarmServiceRequestSerializer(serializers.ModelSerializer):
    tasks = serializers.ListField(write_only=True, required=False)
    puc = serializers.BooleanField(required=False)
    created_by = serializers.SerializerMethodField(read_only=True)
    no_of_tasks = serializers.SerializerMethodField(read_only=True)
    completed = serializers.SerializerMethodField(read_only=True)
    percentage_done = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FarmServiceRequest
        fields = [
            "id",
            "service_name",
            "puc",
            "created_by",
            "tasks",
            "no_of_tasks",
            "completed",
            "percentage_done",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "no_of_tasks",
            "completed",
            "percentage_done",
            "created_at",
            "updated_at",
        ]

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

    def to_internal_value(self, data):
        # Backward compatibility: accept `PUC` from older clients.
        if hasattr(data, "copy"):
            incoming = data.copy()
        elif isinstance(data, dict):
            incoming = dict(data)
        else:
            incoming = data

        if isinstance(incoming, dict) and "puc" not in incoming and "PUC" in incoming:
            incoming["puc"] = incoming.get("PUC")

        return super().to_internal_value(incoming)

    def get_created_by(self, obj):
        user = obj.created_by
        return {"id": user.username, "name": user.get_full_name() or user.username}

    def get_no_of_tasks(self, obj):
        return obj.tasks.count()

    def _progress_counts(self, obj):
        tasks = list(obj.tasks.all())
        total_tasks = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.status)
        return completed_tasks, total_tasks

    def get_completed(self, obj):
        completed, _total = self._progress_counts(obj)
        return completed

    def get_percentage_done(self, obj):
        completed, total = self._progress_counts(obj)
        if total == 0:
            return 0.0
        return round((completed / total) * 100, 2)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tasks"] = FarmServiceTaskReadSerializer(instance.tasks.all(), many=True).data
        return data

    @transaction.atomic
    def create(self, validated_data):
        tasks_data = validated_data.pop("tasks", [])
        request = FarmServiceRequest.objects.create(**validated_data)
        request_user = self.context["request"].user
        for row in tasks_data:
            members = row.pop("team_members", [])
            subtasks = row.pop("subtasks", [])
            task = FarmServiceTask.objects.create(request=request, **row)
            if members:
                task.team_members.set(members)
            for subtask_row in subtasks:
                assigned_member = subtask_row.pop("assigned_member")
                FarmServiceSubtask.objects.create(
                    task=task,
                    assigned_member=assigned_member,
                    created_by=request_user,
                    **subtask_row,
                )
        return request

    @transaction.atomic
    def update(self, instance, validated_data):
        tasks_data = validated_data.pop("tasks", None)
        request_user = self.context["request"].user
        updatable_fields = []

        if "service_name" in validated_data:
            instance.service_name = validated_data["service_name"]
            updatable_fields.append("service_name")
        if "puc" in validated_data:
            instance.puc = validated_data["puc"]
            updatable_fields.append("puc")

        if updatable_fields:
            updatable_fields.append("updated_at")
            instance.save(update_fields=updatable_fields)

        if tasks_data is not None:
            for row in tasks_data:
                task_id = row.pop("id", None)
                members = row.pop("team_members", None)
                subtasks = row.pop("subtasks", None)

                task = None
                if task_id:
                    task = instance.tasks.filter(id=task_id).first()
                    if task is None:
                        raise serializers.ValidationError(
                            {"tasks": f"Invalid task id: {task_id}"}
                        )
                if task is None:
                    if "task_name" not in row:
                        raise serializers.ValidationError(
                            {"tasks": "task_name is required for new task."}
                        )
                    task = FarmServiceTask.objects.create(request=instance, **row)
                else:
                    updatable_fields = []
                    if "task_name" in row:
                        task.task_name = row["task_name"]
                        updatable_fields.append("task_name")
                    if "status" in row:
                        task.status = row["status"]
                        updatable_fields.append("status")
                    if updatable_fields:
                        updatable_fields.append("updated_at")
                        task.save(update_fields=updatable_fields)

                if members is not None:
                    task.team_members.set(members)

                if subtasks is not None:
                    for subtask_row in subtasks:
                        subtask_id = subtask_row.pop("id", None)
                        assigned_member = subtask_row.pop("assigned_member", None)

                        subtask = None
                        if subtask_id:
                            subtask = task.subtasks.filter(id=subtask_id).first()
                            if subtask is None:
                                raise serializers.ValidationError(
                                    {"tasks": f"Invalid subtask id: {subtask_id} for task {task.id}."}
                                )

                        if subtask is None:
                            FarmServiceSubtask.objects.create(
                                task=task,
                                assigned_member=assigned_member,
                                created_by=request_user,
                                **subtask_row,
                            )
                            continue

                        subtask_fields = []
                        if "subtask_name" in subtask_row:
                            subtask.subtask_name = subtask_row["subtask_name"]
                            subtask_fields.append("subtask_name")
                        if "status" in subtask_row:
                            subtask.status = subtask_row["status"]
                            subtask_fields.append("status")
                        if assigned_member is not None:
                            subtask.assigned_member = assigned_member
                            subtask_fields.append("assigned_member")
                        if subtask_fields:
                            subtask_fields.append("updated_at")
                            subtask.save(update_fields=subtask_fields)
        return instance


class FarmServiceRequestListSerializer(serializers.ModelSerializer):
    puc = serializers.BooleanField(required=False)
    created_by = serializers.SerializerMethodField(read_only=True)
    no_of_tasks = serializers.SerializerMethodField(read_only=True)
    completed = serializers.SerializerMethodField(read_only=True)
    percentage_done = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FarmServiceRequest
        fields = [
            "id",
            "service_name",
            "puc",
            "created_by",
            "no_of_tasks",
            "completed",
            "percentage_done",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_created_by(self, obj):
        user = obj.created_by
        return {"id": user.username, "name": user.get_full_name() or user.username}

    def get_no_of_tasks(self, obj):
        return obj.tasks.count()

    def _progress_counts(self, obj):
        tasks = list(obj.tasks.all())
        total_tasks = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.status)
        return completed_tasks, total_tasks

    def get_completed(self, obj):
        completed, _total = self._progress_counts(obj)
        return completed

    def get_percentage_done(self, obj):
        completed, total = self._progress_counts(obj)
        if total == 0:
            return 0.0
        return round((completed / total) * 100, 2)

