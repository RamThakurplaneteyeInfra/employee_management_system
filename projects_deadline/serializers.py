from rest_framework import serializers

from .models import DeadlineProject, DeadlineProjectPhase
from .permissions import can_see_all_phases_for_project, resolve_deadline_employee_id


class PhaseOutputSerializer(serializers.ModelSerializer):
    """Read-only serializer — returns the exact JSON shape the frontend expects."""

    phaseStatus = serializers.CharField(source="phase_status", read_only=True)
    teamLeadId = serializers.IntegerField(source="team_lead_id", read_only=True, allow_null=True)
    memberIds = serializers.JSONField(source="member_ids", read_only=True)

    class Meta:
        model = DeadlineProjectPhase
        fields = [
            "id", "title", "date", "phaseStatus",
            "teamLeadId", "memberIds", "checklist", "notes",
        ]


class ProjectOutputSerializer(serializers.ModelSerializer):
    """Read-only serializer — returns the exact JSON shape the frontend expects."""

    createdBy = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    phases = serializers.SerializerMethodField()

    class Meta:
        model = DeadlineProject
        fields = [
            "id", "title", "branch", "description", "status", "deadline",
            "createdAt", "updatedAt", "createdBy",
            "phases",
        ]

    def get_createdBy(self, obj):
        return obj.created_by_id

    def get_phases(self, obj):
        phases = getattr(obj, "active_phases", None)
        if phases is None:
            phases = obj.phases.filter(archived=False).order_by("sort_order", "created_at")

        request = self.context.get("request") if isinstance(getattr(self, "context", None), dict) else None
        user = getattr(request, "user", None) if request is not None else None

        if user and can_see_all_phases_for_project(user, obj):
            return PhaseOutputSerializer(phases, many=True).data

        employee_id = resolve_deadline_employee_id(user) if user else None
        if employee_id is None:
            return []

        filtered = []
        for p in phases:
            member_ids = getattr(p, "member_ids", None) or []
            if p.team_lead_id == employee_id or employee_id in member_ids:
                filtered.append(p)

        return PhaseOutputSerializer(filtered, many=True).data


class PhaseInputSerializer(serializers.Serializer):
    """Validates a single phase from the incoming payload."""

    title = serializers.CharField(max_length=255)
    date = serializers.DateField(required=False, allow_null=True)
    phase_status = serializers.ChoiceField(
        choices=["PENDING", "IN_PROGRESS", "COMPLETED"],
        required=False, default="PENDING",
    )
    team_lead_id = serializers.IntegerField(required=False, allow_null=True)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list,
    )
    checklist = serializers.ListField(
        child=serializers.DictField(), required=False, default=list,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_checklist(self, value):
        import re
        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")

        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    f"Item {idx} must be an object with 'text', 'checked', and 'checkedDate'."
                )
            if "text" not in item or "checked" not in item:
                raise serializers.ValidationError(
                    f"Item {idx} must have 'text' (string) and 'checked' (boolean)."
                )
            if not isinstance(item["text"], str):
                raise serializers.ValidationError(f"Item {idx} 'text' must be a string.")
            if not isinstance(item["checked"], bool):
                raise serializers.ValidationError(f"Item {idx} 'checked' must be true or false.")

            checked_date = item.get("checkedDate")
            if item["checked"] and checked_date is not None:
                if not isinstance(checked_date, str) or not date_re.match(checked_date):
                    raise serializers.ValidationError(
                        f"Item {idx} 'checkedDate' must be YYYY-MM-DD or null."
                    )
            if not item["checked"]:
                item["checkedDate"] = None
            elif "checkedDate" not in item:
                item["checkedDate"] = None

            employee_ids = item.get("employeeIds", [])
            if employee_ids is None:
                employee_ids = []
            if not isinstance(employee_ids, list):
                raise serializers.ValidationError(
                    f"Item {idx} 'employeeIds' must be an array of integers."
                )
            normalized_ids = []
            for jdx, emp_id in enumerate(employee_ids):
                if not isinstance(emp_id, int):
                    raise serializers.ValidationError(
                        f"Item {idx} 'employeeIds[{jdx}]' must be an integer."
                    )
                normalized_ids.append(emp_id)
            item["employeeIds"] = normalized_ids

        return value


class ProjectInputSerializer(serializers.Serializer):
    """Validates the incoming project payload (POST + PATCH)."""

    title = serializers.CharField(max_length=255, required=True)
    branch = serializers.CharField(max_length=255, required=False, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=["PLANNING", "ACTIVE", "COMPLETED", "ON_HOLD"],
        required=False, default="PLANNING",
    )
    deadline = serializers.DateField(required=False, allow_null=True)
    phases = PhaseInputSerializer(many=True, required=False, default=list)
