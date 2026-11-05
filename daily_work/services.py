"""Load EMS people and keep project membership in sync with daily reports."""

from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.exceptions import ValidationError

from accounts.models import Profile

from .models import DailyProject, ProjectAssignment

INTERN_ROLE = "intern"
TEAM_LEAD_ROLES = frozenset({"teamlead", "teamleader"})
MANAGE_ANY_ROLES = frozenset({"admin", "md"})


def _role_name(user) -> str:
    profile = getattr(user, "accounts_profile", None)
    if profile is None or profile.Role_id is None:
        return ""
    return (profile.Role.role_name or "").strip()


def _role_key(user) -> str:
    return _role_name(user).lower().replace(" ", "")


def is_intern_user(user) -> bool:
    return _role_key(user) == INTERN_ROLE


def is_team_lead_user(user) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    return _role_key(user) in TEAM_LEAD_ROLES or _role_key(user) in MANAGE_ANY_ROLES


def can_manage_any_project(user) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    return _role_key(user) in MANAGE_ANY_ROLES


def can_manage_project(user, project: DailyProject) -> bool:
    if can_manage_any_project(user):
        return True
    return _role_key(user) in TEAM_LEAD_ROLES and project.team_lead_id == user.id


def can_delete_project(user, project: DailyProject) -> bool:
    """Only the project creator or MD may delete a project."""
    if getattr(user, "is_superuser", False):
        return True
    if _role_key(user) == "md":
        return True
    return project.team_lead_id == user.id


def display_name(user) -> str:
    profile = getattr(user, "accounts_profile", None)
    name = (getattr(profile, "Name", None) or "").strip()
    return name or user.get_full_name() or user.username


def profile_for_user(user):
    return (
        Profile.objects.filter(Employee_id=user)
        .select_related("Role")
        .prefetch_related("functions")
        .first()
    )


def _people_queryset():
    return (
        User.objects.filter(is_active=True, accounts_profile__isnull=False)
        .select_related("accounts_profile__Role")
        .order_by("accounts_profile__Name", "id")
    )


def list_people(*, interns: bool) -> list[dict]:
    rows = []
    for user in _people_queryset():
        if is_intern_user(user) != interns:
            continue
        rows.append(
            {
                "id": user.id,
                "name": display_name(user),
                "username": user.username,
            }
        )
    return rows


def _parse_id_list(value, label: str):
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValidationError({label: "Must be a list of EMS user ids."})
    parsed = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, str)):
            raise ValidationError({label: "Each id must be an integer."})
        text = str(item).strip()
        if not text.isdigit():
            raise ValidationError({label: "Each id must be an integer."})
        parsed.append(int(text))
    if len(parsed) != len(set(parsed)):
        raise ValidationError({label: "Duplicate ids are not allowed."})
    return parsed


def _load_members(user_ids: list[int], *, interns: bool) -> list[User]:
    if not user_ids:
        return []
    label = "interns" if interns else "employees"
    found = {
        user.id: user
        for user in User.objects.filter(id__in=user_ids, is_active=True).select_related(
            "accounts_profile__Role"
        )
    }
    missing = [user_id for user_id in user_ids if user_id not in found]
    if missing:
        raise ValidationError(
            {label: f"Unknown or inactive EMS ids: {missing}."}
        )
    chosen = []
    for user_id in user_ids:
        user = found[user_id]
        if not hasattr(user, "accounts_profile"):
            raise ValidationError({label: f"User {user_id} has no EMS profile."})
        if is_intern_user(user) != interns:
            expected = "an intern" if interns else "an employee"
            raise ValidationError({label: f"User {user_id} is not {expected}."})
        chosen.append(user)
    return chosen


@transaction.atomic
def apply_assignments(project: DailyProject, employees, interns) -> None:
    """
    Replace the employee list, the intern list, or both.

    None leaves that list unchanged. Historical DailyWorkReport rows stay.
    """
    employee_ids = _parse_id_list(employees, "employees")
    intern_ids = _parse_id_list(interns, "interns")
    if employee_ids is None and intern_ids is None:
        return

    current = {
        row.user_id: row
        for row in ProjectAssignment.objects.filter(project=project)
    }
    if employee_ids is None:
        employee_ids = [
            user_id
            for user_id, row in current.items()
            if row.member_type == ProjectAssignment.MemberType.EMPLOYEE
        ]
    if intern_ids is None:
        intern_ids = [
            user_id
            for user_id, row in current.items()
            if row.member_type == ProjectAssignment.MemberType.INTERN
        ]

    overlap = set(employee_ids) & set(intern_ids)
    if overlap:
        raise ValidationError(
            {
                "employees": (
                    "A person cannot be both an employee and an intern "
                    f"on the same project: {sorted(overlap)}."
                )
            }
        )

    _load_members(employee_ids, interns=False)
    _load_members(intern_ids, interns=True)

    wanted = {
        user_id: ProjectAssignment.MemberType.EMPLOYEE for user_id in employee_ids
    }
    wanted.update(
        {user_id: ProjectAssignment.MemberType.INTERN for user_id in intern_ids}
    )

    ProjectAssignment.objects.filter(project=project).exclude(
        user_id__in=wanted.keys()
    ).delete()

    for user_id, member_type in wanted.items():
        row = current.get(user_id)
        if row is None:
            ProjectAssignment.objects.create(
                project=project,
                user_id=user_id,
                member_type=member_type,
            )
            continue
        if row.member_type != member_type:
            row.member_type = member_type
            row.save(update_fields=["member_type"])


def assignment_payload(project: DailyProject, viewer=None) -> dict:
    employee_ids = []
    intern_ids = []
    for row in project.assignments.all().order_by("user_id"):
        if row.member_type == ProjectAssignment.MemberType.INTERN:
            intern_ids.append(row.user_id)
        else:
            employee_ids.append(row.user_id)
    payload = {
        "project_id": project.id,
        "project_name": project.project_name,
        "project_description": project.project_description,
        "team_lead_id": project.team_lead_id,
        "employees": employee_ids,
        "interns": intern_ids,
        "status": project.status,
    }
    if viewer is not None:
        payload["can_delete"] = can_delete_project(viewer, project)
    return payload


def user_is_assigned(project: DailyProject, user) -> bool:
    return ProjectAssignment.objects.filter(project=project, user=user).exists()
