"""
MD approval fields on project phase checklist items (JSON).

Statuses:
- Pending (default)
- Approved (MD accepted — only then scoring points are allocated)
- Incomplete (MD marked incomplete — no points)

Scoring uses checkedDate month; points require checked + Approved.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone as dt_timezone

MD_APPROVAL_PENDING = "Pending"
MD_APPROVAL_APPROVED = "Approved"
MD_APPROVAL_INCOMPLETE = "Incomplete"
MD_APPROVAL_STATUSES = frozenset(
    {MD_APPROVAL_PENDING, MD_APPROVAL_APPROVED, MD_APPROVAL_INCOMPLETE}
)


def new_checklist_item_id() -> str:
    return str(uuid.uuid4())


def _utcnow_iso() -> str:
    return datetime.now(dt_timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_md_approval_fields(
    item: dict,
    *,
    was_checked: bool | None = None,
    for_output: bool = False,
) -> dict:
    """
    Ensure MD fields exist and apply reset rules.
    - Unchecked → Pending, clear approve metadata
    - Newly checked (False→True) → Pending
    - Missing status on write → Pending
    - Missing status on output + checked → Approved (legacy pre-migration rows)
    """
    if not isinstance(item, dict):
        return item

    if not item.get("id"):
        item["id"] = new_checklist_item_id()

    checked = bool(item.get("checked"))
    raw_status = item.get("mdApproval")
    status = (raw_status or "").strip() if isinstance(raw_status, str) else ""

    if not checked:
        item["mdApproval"] = MD_APPROVAL_PENDING
        item["mdApprovedAt"] = None
        item["mdApprovedBy"] = None
        if item.get("mdNote") is None:
            item["mdNote"] = ""
        elif not isinstance(item.get("mdNote"), str):
            item["mdNote"] = str(item.get("mdNote") or "")
        return item

    # Newly checked: force Pending for MD review
    if was_checked is False and checked:
        item["mdApproval"] = MD_APPROVAL_PENDING
        item["mdApprovedAt"] = None
        item["mdApprovedBy"] = None
        if item.get("mdNote") is None:
            item["mdNote"] = ""
        return item

    if not status:
        item["mdApproval"] = (
            MD_APPROVAL_APPROVED if (for_output and checked) else MD_APPROVAL_PENDING
        )
    elif status not in MD_APPROVAL_STATUSES:
        item["mdApproval"] = MD_APPROVAL_PENDING
    else:
        item["mdApproval"] = status

    if item.get("mdApprovedAt") is not None and not isinstance(item.get("mdApprovedAt"), str):
        item["mdApprovedAt"] = None
    if item.get("mdApprovedBy") is not None and not isinstance(item.get("mdApprovedBy"), str):
        item["mdApprovedBy"] = None
    if item.get("mdNote") is None:
        item["mdNote"] = ""
    elif not isinstance(item.get("mdNote"), str):
        item["mdNote"] = str(item.get("mdNote") or "")

    return item


def checklist_item_counts_for_scoring(item: dict) -> bool:
    """Points only when checked and MD Approved (legacy missing status counts as Approved)."""
    if not isinstance(item, dict) or not item.get("checked"):
        return False
    status = (item.get("mdApproval") or "").strip()
    if not status:
        return True
    return status == MD_APPROVAL_APPROVED


def is_pending_md_approval_item(item: dict) -> bool:
    """Checked item waiting for MD (Pending)."""
    if not isinstance(item, dict) or not item.get("checked"):
        return False
    status = (item.get("mdApproval") or "").strip()
    # Missing status on checked is treated as historically Approved, not pending
    if not status:
        return False
    return status == MD_APPROVAL_PENDING


def is_incomplete_md_approval_item(item: dict) -> bool:
    """Checked item marked Incomplete by MD."""
    if not isinstance(item, dict) or not item.get("checked"):
        return False
    status = (item.get("mdApproval") or "").strip()
    return status == MD_APPROVAL_INCOMPLETE


def count_md_approval_checklists() -> dict[str, int]:
    """
    Count checked checklist items by MD status on active (non-archived) phases/projects.
    Returns pending and incomplete counts.
    """
    from .models import DeadlineProjectPhase

    pending = 0
    incomplete = 0
    phases = (
        DeadlineProjectPhase.objects.filter(archived=False, project__archived=False)
        .only("id", "checklist")
        .iterator(chunk_size=200)
    )
    for phase in phases:
        for item in phase.checklist or []:
            if is_pending_md_approval_item(item):
                pending += 1
            elif is_incomplete_md_approval_item(item):
                incomplete += 1
    return {"pending": pending, "incomplete": incomplete}


def count_pending_md_approval_checklists() -> int:
    """Count checked + Pending checklist items (compat wrapper)."""
    return count_md_approval_checklists()["pending"]


def merge_preserved_md_fields(incoming: dict, previous: dict | None, *, requester_is_md: bool = False) -> dict:
    """
    Project PATCH must not change MD approval (use the dedicated MD endpoint).
    Preserve prior MD fields when item id matches; reset on uncheck / newly checked.
    """
    if not isinstance(incoming, dict):
        return incoming

    prev = previous if isinstance(previous, dict) else None
    was_checked = bool(prev.get("checked")) if prev else None
    now_checked = bool(incoming.get("checked"))

    if prev and prev.get("id") and not incoming.get("id"):
        incoming["id"] = prev["id"]

    # Uncheck → always Pending
    if not now_checked:
        incoming["mdApproval"] = MD_APPROVAL_PENDING
        incoming["mdApprovedAt"] = None
        incoming["mdApprovedBy"] = None
        if not isinstance(incoming.get("mdNote"), str):
            incoming["mdNote"] = ""
        normalize_md_approval_fields(incoming, was_checked=was_checked)
        return incoming

    # Newly checked → Pending for MD review
    if was_checked is False:
        incoming["mdApproval"] = MD_APPROVAL_PENDING
        incoming["mdApprovedAt"] = None
        incoming["mdApprovedBy"] = None
        if not isinstance(incoming.get("mdNote"), str):
            incoming["mdNote"] = ""
        normalize_md_approval_fields(incoming, was_checked=was_checked)
        return incoming

    # Still checked with prior item → keep previous MD decision (PATCH cannot change it)
    if prev is not None and was_checked:
        incoming["mdApproval"] = prev.get("mdApproval") or MD_APPROVAL_PENDING
        incoming["mdApprovedAt"] = prev.get("mdApprovedAt")
        incoming["mdApprovedBy"] = prev.get("mdApprovedBy")
        incoming["mdNote"] = prev.get("mdNote") if isinstance(prev.get("mdNote"), str) else ""
        normalize_md_approval_fields(incoming, was_checked=was_checked)
        return incoming

    # Brand-new checked item → Pending
    incoming["mdApproval"] = MD_APPROVAL_PENDING
    incoming["mdApprovedAt"] = None
    incoming["mdApprovedBy"] = None
    if not isinstance(incoming.get("mdNote"), str):
        incoming["mdNote"] = ""
    normalize_md_approval_fields(incoming, was_checked=was_checked)
    return incoming


def apply_md_approval_to_item(
    item: dict,
    *,
    md_approval: str,
    md_note: str,
    approved_by: str,
) -> dict:
    status = (md_approval or "").strip()
    if status not in (MD_APPROVAL_APPROVED, MD_APPROVAL_INCOMPLETE):
        raise ValueError("mdApproval must be 'Approved' or 'Incomplete'")
    if not item.get("checked"):
        raise ValueError("Only checked checklist items can be MD-approved")

    item["mdApproval"] = status
    item["mdNote"] = md_note or ""
    item["mdApprovedBy"] = approved_by
    item["mdApprovedAt"] = _utcnow_iso()
    return item


def index_checklist_md_by_id(phases) -> dict[str, dict]:
    """Map checklist item id → item dict from active phases."""
    out: dict[str, dict] = {}
    for phase in phases:
        for item in phase.checklist or []:
            if isinstance(item, dict) and item.get("id"):
                out[str(item["id"])] = item
    return out
