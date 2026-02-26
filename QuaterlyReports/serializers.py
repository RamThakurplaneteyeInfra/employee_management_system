from ems.RequiredImports import serializers
from .models import Functions, FunctionsGoals, ActionableGoals, FunctionsEntries
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
    status = serializers.SlugRelatedField(
        slug_field="status_name",
        queryset=TaskStatus.objects.all(),
        required=False,
        allow_null=True,
    )
    final_Status = serializers.SlugRelatedField(
        slug_field="status_name",
        queryset=TaskStatus.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = FunctionsEntries
        fields = [
            "id", "goal", "Creator", "co_author", "share_with", "approved_by_coauthor",
            "date", "time", "status", "final_Status", "note",
        ]
        read_only_fields = ["time", "Creator"]

    def create(self, validated_data):
        if validated_data.get("status") is None:
            validated_data["status"] = _get_pending_status()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        username = getattr(request.user, "username", None) if request and request.user else None
        # Only co_author can change approved_by_coauthor
        if "approved_by_coauthor" in validated_data:
            if str(instance.co_author_id or "") != str(username or ""):
                validated_data.pop("approved_by_coauthor", None)
            elif validated_data.get("approved_by_coauthor") is True:
                inprogress = _get_inprogress_status()
                if inprogress:
                    validated_data["status"] = inprogress
        # Only share_with can change final_Status
        if "final_Status" in validated_data and str(instance.share_with_id or "") != str(username or ""):
            validated_data.pop("final_Status", None)
        # Only creator can change status; creator may set status to Completed only after final_Status is Completed
        if "status" in validated_data:
            creator_id = instance.Creator_id
            if str(creator_id) != str(username or ""):
                validated_data.pop("status", None)
            else:
                new_status = validated_data.get("status")
                if new_status and getattr(new_status, "status_name", None) == "COMPLETED":
                    final = instance.final_Status
                    if not final or getattr(final, "status_name", None) != "COMPLETED":
                        validated_data.pop("status", None)
        return super().update(instance, validated_data)
        # notes = validated_data.pop('note')
        # # creator = validated_data.get('Creator')
        
        # # If 'note' is a list, create multiple entries
        # if isinstance(notes, list):
        #     entries = [
        #         FunctionsEntries(**validated_data, note=n) 
        #         for n in notes
        #     ]
        #     # bulk_create is highly optimized for performance
        #     return FunctionsEntries.objects.bulk_create(entries)
        
        # # If 'note' is a single string, create normally
        # return FunctionsEntries.objects.create(note=notes, **validated_data)
