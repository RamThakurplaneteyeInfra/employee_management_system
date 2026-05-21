"""Grouped certificate JSON: { id, name, certificate: [{ id, title, desc, link }, ...] }."""
from collections import OrderedDict

from accounts.filters import _get_users_Name_sync

from .s3_helpers import certificate_file_url


def _employee_display_name(user):
    profile = getattr(user, "accounts_profile", None)
    if profile and profile.Name:
        return profile.Name
    return _get_users_Name_sync(user) or user.username


def certificate_item(cert):
    return {
        "id": cert.pk,
        "title": cert.title or "",
        "desc": cert.description or "",
        "link": certificate_file_url(cert.s3_key),
    }


def employee_group(user, certificates):
    """Build one grouped object for an employee."""
    certs = sorted(certificates, key=lambda c: (c.created_at, c.pk), reverse=True)
    return {
        "id": user.username,
        "name": _employee_display_name(user),
        "certificate": [certificate_item(c) for c in certs],
    }


def grouped_list_from_certificates(certificates):
    """
    Group active certificate rows by employee.
    Returns list of { id, name, certificate: [...] }, ordered by employee id.
    """
    by_employee = OrderedDict()
    for cert in certificates:
        user = cert.employee
        key = user.pk
        if key not in by_employee:
            by_employee[key] = {"user": user, "certs": []}
        by_employee[key]["certs"].append(cert)
    groups = [employee_group(entry["user"], entry["certs"]) for entry in by_employee.values()]
    return sorted(groups, key=lambda g: g["id"])


def grouped_single_for_user(user, certificates):
    """One employee wrapper (may have empty certificate array)."""
    return employee_group(user, list(certificates))
