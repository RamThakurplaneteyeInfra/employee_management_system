from ems.RequiredImports import serializers
from .models import Functions, FunctionsGoals, ActionableGoals, FunctionsEntries, FunctionsEntriesShare
from task_management.models import TaskStatus


def _get_pending_status():
    try:
        return TaskStatus.objects.get(status_name="PENDING")
    except TaskStatus.DoesNotExist:
        return None


def _get_inprogress_status():
    try:
        return TaskStatus.objects.get(status_name="INPROCESS")
    except TaskStatus.DoesNotExist:
        return None


def _get_completed_status():
    try:
        return TaskStatus.objects.get(status_name="COMPLETED")
    except TaskStatus.DoesNotExist:
        return None


class FunctionsEntriesShareSerializer(serializers.ModelSerializer):
    """One share in the chain: shared_with username, note, shared_time, individual_status."""
    shared_with_username = serializers.CharField(source="shared_with.username", read_only=True)
    individual_status_name = serializers.CharField(
        source="individual_status.status_name", read_only=True, allow_null=True
    )

    class Meta:
        model = FunctionsEntriesShare
        fields = [
            "id", "actionable_entry", "shared_with", "shared_with_username",
            "note", "shared_time", "individual_status", "individual_status_name",
        ]
        read_only_fields = ["shared_time", "actionable_entry"]


class ActionableGoalSerializer(serializers.ModelSerializer):
    Actionable_id = serializers.IntegerField(source='id', read_only=True)
    class Meta:
        model = ActionableGoals
        fields = ['Actionable_id', 'purpose', 'grp']

class FunctionGoalSerializer(serializers.ModelSerializer):
    actionable_goals = ActionableGoalSerializer(source='actionablegoals_set', many=True, read_only=True)
    Functional_goal_id = serializers.IntegerField(source='id', read_only=True)
    class Meta:
        model = FunctionsGoals
        fields = ['Functional_goal_id', 'Maingoal', 'actionable_goals']

class FunctionDetailSerializer(serializers.ModelSerializer):
    functional_goals = FunctionGoalSerializer(source='functionsgoals_set', many=True, read_only=True)
    Functional_id = serializers.IntegerField(source='id', read_only=True)
    class Meta:
        model = Functions
        fields = ['Functional_id', 'function', 'functional_goals']


class FunctionsEntriesSerializer(serializers.ModelSerializer):
    final_Status = serializers.SlugRelatedField(
        slug_field="status_name",
        queryset=TaskStatus.objects.all(),
        required=False,
        allow_null=True,
    )
    share_chain = FunctionsEntriesShareSerializer(many=True, read_only=True)
    share_with = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = FunctionsEntries
        fields = [
            "id", "goal", "Creator", "co_author", "share_with", "approved_by_coauthor",
            "date", "time", "final_Status", "note", "share_chain",
        ]
        read_only_fields = ["time", "Creator"]

    def create(self, validated_data):
        first_share_username = validated_data.pop("share_with", "").strip() or None
        if not validated_data.get("final_Status"):
            validated_data["final_Status"] = _get_pending_status()
        instance = super().create(validated_data)
        if first_share_username:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(username=first_share_username)
                FunctionsEntriesShare.objects.create(
                    actionable_entry=instance,
                    shared_with=user,
                    note="",
                    individual_status=_get_pending_status(),
                )
            except Exception:
                pass
        return instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        username = getattr(request.user, "username", None) if request and request.user else None
        validated_data.pop("share_with", None)
        # Only co_author can set approved_by_coauthor; when True, set final_Status to Inprogress
        if "approved_by_coauthor" in validated_data:
            if str(instance.co_author_id or "") != str(username or ""):
                validated_data.pop("approved_by_coauthor", None)
            elif validated_data.get("approved_by_coauthor") is True:
                inprogress = _get_inprogress_status()
                if inprogress:
                    validated_data["final_Status"] = inprogress
        # Only creator can change final_Status; creator can set Completed only when they choose (final status)
        if "final_Status" in validated_data:
            if str(instance.Creator_id or "") != str(username or ""):
                validated_data.pop("final_Status", None)
        return super().update(instance, validated_data)
