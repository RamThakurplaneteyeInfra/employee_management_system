from ems.RequiredImports import serializers
from ems.utils import gmt_to_ist_str
from project.models import Product
from .models import Functions, FunctionsGoals, ActionableGoals, FunctionsEntries, FunctionsEntriesShare
from .npc_goals import (
    create_actionable_goal_from_text,
    normalize_goal_text,
    user_can_use_free_text_goal,
)
from task_management.models import TaskStatus


def _get_user_display_name(user):
    """Return Profile.Name for user if available, else username. Use with prefetch_related('accounts_profile')."""
    if not user:
        return None
    try:
        profile = getattr(user, "accounts_profile", None)
        return profile.Name if profile and getattr(profile, "Name", None) else user.username
    except Exception:
        return user.username


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
    """One share in the chain: shared_with_name (Profile), shared_note, shared_time, status_name only."""
    shared_with_name = serializers.SerializerMethodField()
    shared_time = serializers.SerializerMethodField()
    status_name = serializers.CharField(
        source="individual_status.status_name", read_only=True, allow_null=True
    )

    class Meta:
        model = FunctionsEntriesShare
        fields = [
            "id", "actionable_entry", "shared_with_name",
            "shared_note", "shared_time", "status_name",
        ]
        read_only_fields = ["shared_time", "actionable_entry"]

    def get_shared_with_name(self, obj):
        return _get_user_display_name(getattr(obj, "shared_with", None))

    def get_shared_time(self, obj):
        return gmt_to_ist_str(obj.shared_time, "%d/%m/%Y %H:%M:%S") if obj.shared_time else None


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
    """Actionable entry: creator/co_author names, original_entry (creator text), share_chain with shared_note. Create accepts share_with + shared_note for first share."""
    creator_name = serializers.SerializerMethodField()
    co_author_name = serializers.SerializerMethodField()
    co_author = serializers.CharField(write_only=True, required=True, allow_blank=False)
    product_name = serializers.SerializerMethodField()
    product = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    final_Status = serializers.SlugRelatedField(
        slug_field="status_name",
        queryset=TaskStatus.objects.all(),
        required=False,
        allow_null=True,
    )
    share_chain = FunctionsEntriesShareSerializer(many=True, read_only=True)
    share_with = serializers.CharField(write_only=True, required=True, allow_blank=False)
    shared_note = serializers.CharField(write_only=True, required=False, allow_blank=True)
    goal_text = serializers.SerializerMethodField()
    time = serializers.TimeField(format="%H:%M:%S", read_only=True)

    class Meta:
        model = FunctionsEntries
        fields = [
            "id", "goal", "goal_text", "product", "product_name", "creator_name", "co_author_name", "co_author",
            "share_with", "shared_note", "approved_by_coauthor", "co_author_note", "date", "time",
            "final_Status", "original_entry", "share_chain",
        ]
        read_only_fields = ["time", "goal_text"]
        extra_kwargs = {
            "goal": {"required": False, "allow_null": True},
        }

    def get_goal_text(self, obj):
        goal = getattr(obj, "goal", None)
        if goal is None:
            return None
        return getattr(goal, "purpose", None) or None

    def _extract_incoming_goal_text(self) -> str:
        data = getattr(self, "initial_data", None) or {}
        if not isinstance(data, dict):
            return ""
        raw = data.get("goal_text")
        if raw is None:
            raw = data.get("goal_name")
        return normalize_goal_text(raw)

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def validate_product(self, value):
        """Accept product as full product name (string); resolve to Product instance or None."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        name = value.strip() if isinstance(value, str) else str(value)
        try:
            return Product.objects.get(name__iexact=name)
        except Product.DoesNotExist:
            from rest_framework import serializers as s
            raise s.ValidationError("Product with this name does not exist.")

    def get_creator_name(self, obj):
        return _get_user_display_name(getattr(obj, "Creator", None))

    def get_co_author_name(self, obj):
        return _get_user_display_name(getattr(obj, "co_author", None))

    def validate_co_author(self, value):
        if not value or (isinstance(value, str) and not value.strip()):
            from rest_framework import serializers as s
            raise s.ValidationError("co_author (username) is required when creating an actionable entry.")
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(username=value.strip())
        except User.DoesNotExist:
            from rest_framework import serializers as s
            raise s.ValidationError("User with this username does not exist.")

    def validate(self, attrs):
        if not self.instance:
            from rest_framework import serializers as s

            goal_text = self._extract_incoming_goal_text()
            has_goal = attrs.get("goal") is not None
            has_goal_text = bool(goal_text)
            if not has_goal and not has_goal_text:
                raise s.ValidationError(
                    {
                        "goal": [
                            "goal (Goal_id) or goal_text is required when creating an actionable entry."
                        ]
                    }
                )
            if has_goal_text and not has_goal:
                request = self.context.get("request")
                user = getattr(request, "user", None) if request else None
                if not user_can_use_free_text_goal(user):
                    raise s.ValidationError(
                        {
                            "goal_text": [
                                "Free-text goals are only allowed for employees with the NPC function "
                                "or Intern role. Use goal (catalog Goal_id) instead."
                            ]
                        }
                    )
                self.context["pending_goal_text"] = goal_text
            if not attrs.get("co_author"):
                raise s.ValidationError(
                    {"co_author": "co_author (username) is required when creating an actionable entry."}
                )
            sw = attrs.get("share_with")
            if not sw or (isinstance(sw, str) and not sw.strip()):
                raise s.ValidationError(
                    {"share_with": "share_with (username) is required when creating an actionable entry."}
                )
        return attrs

    def create(self, validated_data):
        first_share_username = (validated_data.pop("share_with", "") or "").strip() or None
        first_shared_note = (validated_data.pop("shared_note", "") or "").strip() or ""
        validated_data.pop("co_author_note", None)  # Only co_author can set this (on update)
        pending_goal_text = self.context.pop("pending_goal_text", "")
        if validated_data.get("goal") is None and pending_goal_text:
            validated_data["goal"] = create_actionable_goal_from_text(pending_goal_text)
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
                    shared_note=first_shared_note,
                    individual_status=_get_pending_status(),
                )
            except Exception:
                pass
        return instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        username = getattr(request.user, "username", None) if request and request.user else None
        validated_data.pop("share_with", None)
        validated_data.pop("shared_note", None)
        # Only co_author can set approved_by_coauthor and co_author_note
        if "co_author_note" in validated_data and str(instance.co_author_id or "") != str(username or ""):
            validated_data.pop("co_author_note", None)
        # Only co_author can set approved_by_coauthor; when True, set final_Status to INPROCESS
        status_set_by_approval = False
        if "approved_by_coauthor" in validated_data:
            if str(instance.co_author_id or "") != str(username or ""):
                validated_data.pop("approved_by_coauthor", None)
            elif validated_data.get("approved_by_coauthor") is True:
                inprogress = _get_inprogress_status()
                if inprogress:
                    validated_data["final_Status"] = inprogress
                    status_set_by_approval = True
        # Only creator can set final_Status to COMPLETED; creator cannot set INPROCESS (only co_author approval can).
        # Creator can set COMPLETED only after all share_chain users have marked their individual_status as COMPLETED.
        if "final_Status" in validated_data:
            if str(instance.Creator_id or "") != str(username or "") and not status_set_by_approval:
                validated_data.pop("final_Status", None)
            elif str(instance.Creator_id or "") == str(username or ""):
                st = validated_data.get("final_Status")
                if st and getattr(st, "status_name", "").upper() == "INPROCESS":
                    validated_data.pop("final_Status", None)
                elif st and getattr(st, "status_name", "").upper() == "COMPLETED":
                    # Creator may set COMPLETED only when all share_chain users have completed (or there is no share chain).
                    from .models import FunctionsEntriesShare
                    share_count = FunctionsEntriesShare.objects.filter(actionable_entry=instance).count()
                    if share_count > 0:
                        completed_count = FunctionsEntriesShare.objects.filter(
                            actionable_entry=instance, individual_status__status_name="COMPLETED"
                        ).count()
                        if completed_count != share_count:
                            validated_data.pop("final_Status", None)
                            from rest_framework import serializers as s
                            raise s.ValidationError({
                                "final_Status": "You may set final status to Completed only after all share-chain users have marked their status as Completed."
                            })
        return super().update(instance, validated_data)
