from accounts.filters import _get_user_role_sync


def _role_name(user):
    try:
        return (_get_user_role_sync(user) or "").strip()
    except Exception:
        return ""


def resolve_deadline_employee_id(user):
    """
    Single id for phase team_lead_id / member_ids comparisons.
    Prefer numeric username (employee id); else Django user pk.
    """
    if not user or not user.is_authenticated:
        return None
    uname = getattr(user, "username", None)
    if uname is not None:
        try:
            return int(str(uname).strip())
        except (TypeError, ValueError):
            pass
    return getattr(user, "id", None)


def is_global_privileged_deadline_user(user):
    """See all projects / all phases: superuser, MD, Admin, or TeamLead."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _role_name(user) in ("MD", "Admin", "TeamLead")


def can_see_all_phases_for_project(user, project):
    """Full phase list for this project: global privileged or project creator."""
    if not user or not user.is_authenticated or project is None:
        return False
    if is_global_privileged_deadline_user(user):
        return True
    return project.created_by_id == getattr(user, "id", None)


def can_edit_project(user, project=None):
    """
    Create / update / soft-delete: superuser, MD, Admin, or the project creator (per project).
    POST passes project=None → only superuser / MD / Admin may create.
    """
    if not user or not user.is_authenticated:
        return False

    if is_global_privileged_deadline_user(user):
        return True

    if project is not None and project.created_by_id == user.id:
        return True

    return False
