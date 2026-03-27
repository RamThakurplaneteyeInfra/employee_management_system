from accounts.filters import _get_user_role_sync


def can_edit_project(user, project=None):
    """
    Returns True when the user is allowed to create / update / soft-delete.
    Allowed: MD, Admin, superuser, or the project creator.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    role = (_get_user_role_sync(user) or "").strip()
    if role in ("MD", "Admin"):
        return True

    if project is not None and project.created_by_id == user.id:
        return True

    return False
