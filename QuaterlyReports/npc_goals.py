"""
Free-text actionable goals (NPC / DM function + Intern role): auto-create ActionableGoals rows.

Free-text goals are stored under a dedicated FunctionsGoals bucket and are excluded
from GET /get_functions_and_actionable_goals/ so the catalog API is not polluted.
"""
from __future__ import annotations

from accounts.models import Functions, Profile

from .models import ActionableGoals, FunctionsGoals

NPC_FUNCTION_LABEL = "NPC"
DM_FUNCTION_LABEL = "DM"
INTERN_ROLE_NAME = "Intern"
NPC_USER_GOALS_MAIN_LABEL = "NPC user goals"
NPC_GOAL_TEXT_MAX_LENGTH = 255


def _user_has_function(user, function_label: str) -> bool:
    """True when the user's profile includes the given function (case-insensitive)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    label = (function_label or "").strip().upper()
    if not label:
        return False
    profile = (
        Profile.objects.filter(Employee_id=user)
        .prefetch_related("functions")
        .first()
    )
    if not profile:
        return False
    for fn in profile.functions.all():
        if (getattr(fn, "function", None) or "").strip().upper() == label:
            return True
    return False


def user_has_npc_function(user) -> bool:
    """True when the user's profile includes the NPC function."""
    return _user_has_function(user, NPC_FUNCTION_LABEL)


def user_has_dm_function(user) -> bool:
    """True when the user's profile includes the DM function."""
    return _user_has_function(user, DM_FUNCTION_LABEL)


def user_has_intern_role(user) -> bool:
    """True when the user's profile Role is Intern."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    profile = (
        Profile.objects.filter(Employee_id=user)
        .select_related("Role")
        .first()
    )
    if not profile or not profile.Role:
        return False
    return (profile.Role.role_name or "").strip() == INTERN_ROLE_NAME


def user_can_use_free_text_goal(user) -> bool:
    """NPC/DM function or Intern role may create entries with goal_text instead of catalog goal."""
    return (
        user_has_npc_function(user)
        or user_has_dm_function(user)
        or user_has_intern_role(user)
    )


def get_or_create_npc_function() -> Functions:
    fn, _ = Functions.objects.get_or_create(function=NPC_FUNCTION_LABEL)
    return fn


def get_or_create_npc_user_goals_bucket() -> FunctionsGoals:
    function_obj = get_or_create_npc_function()
    bucket, _ = FunctionsGoals.objects.get_or_create(
        Function=function_obj,
        Maingoal=NPC_USER_GOALS_MAIN_LABEL,
    )
    return bucket


def is_npc_user_goals_bucket(functions_goal: FunctionsGoals | None) -> bool:
    if functions_goal is None:
        return False
    return (getattr(functions_goal, "Maingoal", None) or "").strip() == NPC_USER_GOALS_MAIN_LABEL


def normalize_goal_text(raw) -> str:
    text = (raw or "").strip() if isinstance(raw, str) else str(raw or "").strip()
    if len(text) > NPC_GOAL_TEXT_MAX_LENGTH:
        text = text[:NPC_GOAL_TEXT_MAX_LENGTH]
    return text


def create_actionable_goal_from_text(goal_text: str) -> ActionableGoals:
    """Create an ActionableGoals row for NPC user-entered goal text."""
    text = normalize_goal_text(goal_text)
    if not text:
        raise ValueError("goal_text cannot be empty")
    bucket = get_or_create_npc_user_goals_bucket()
    return ActionableGoals.objects.create(
        FunctionGoal=bucket,
        purpose=text,
        grp=None,
    )
