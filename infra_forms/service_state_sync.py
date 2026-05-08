"""Keep `StructureEntry` legacy BOQ/LiDAR/SAR columns in sync with `StructureEntryServiceState`."""

from __future__ import annotations

from django.db import transaction

from .models import InfraServiceType, StructureEntry, StructureEntryServiceState

LEGACY_CODES = ("boq", "lidar", "sar")

_DEFAULT_LABELS = {
    "boq": "BOQ Physical",
    "lidar": "LiDAR",
    "sar": "SAR",
}


def _allowed_status_codes() -> set[str]:
    return {c[0] for c in StructureEntry.INSPECTION_STATUS_CHOICES}


def mirror_legacy_columns_to_service_states(entry: StructureEntry) -> None:
    """Use legacy *_status / *_remark / has_* as source of truth for the three built-in services."""
    type_map = {
        t.code: t for t in InfraServiceType.objects.filter(code__in=LEGACY_CODES)
    }
    allowed = _allowed_status_codes()
    for code in LEGACY_CODES:
        stype = type_map.get(code)
        if not stype:
            continue
        status_val = (getattr(entry, f"{code}_status") or "").strip()
        if status_val and status_val not in allowed:
            status_val = ""
        remark_val = getattr(entry, f"{code}_remark") or ""
        has_mod = bool(getattr(entry, f"has_{code}"))
        has_content = bool(status_val) or bool((remark_val or "").strip())
        if not has_mod and not has_content:
            StructureEntryServiceState.objects.filter(
                structure_entry=entry, service_type=stype
            ).delete()
            continue
        StructureEntryServiceState.objects.update_or_create(
            structure_entry=entry,
            service_type=stype,
            defaults={
                "inspection_status": status_val,
                "remark": remark_val,
            },
        )


def mirror_service_states_to_legacy_columns(entry: StructureEntry) -> None:
    """Populate boq/lidar/sar columns and has_* from related service state rows."""
    type_map = {
        t.code: t for t in InfraServiceType.objects.filter(code__in=LEGACY_CODES)
    }
    if not type_map:
        return
    rows_by_code: dict[str, StructureEntryServiceState] = {}
    for row in (
        StructureEntryServiceState.objects.filter(
            structure_entry=entry,
            service_type_id__in=[t.id for t in type_map.values()],
        ).select_related("service_type")
    ):
        code = row.service_type.code
        if code in type_map:
            rows_by_code[code] = row

    allowed = _allowed_status_codes()
    changed = []
    for code in LEGACY_CODES:
        row = rows_by_code.get(code)
        if row is None:
            status_val, remark_val = "", ""
        else:
            status_val = (row.inspection_status or "").strip()
            if status_val and status_val not in allowed:
                status_val = ""
            remark_val = row.remark or ""
        setattr(entry, f"{code}_status", status_val)
        setattr(entry, f"{code}_remark", remark_val or "")
        setattr(
            entry,
            f"has_{code}",
            bool(status_val) or bool((remark_val or "").strip()),
        )
        changed.extend([f"{code}_status", f"{code}_remark", f"has_{code}"])
    if changed:
        entry.save(update_fields=[*changed, "updated_at"])


def upsert_service_states_merge(
    entry: StructureEntry, items: list[dict[str, str]]
) -> None:
    """
    Create/update rows for listed codes only (PATCH merge semantics).

    ``items``: ``[{code, inspection_status?, remark?}, ...]`` with normalized keys.
    """
    if not items:
        return
    codes = [x["code"] for x in items]
    types = {t.code: t for t in InfraServiceType.objects.filter(code__in=codes, active=True)}
    missing = sorted(set(codes) - set(types))
    if missing:
        raise ValueError(f"Unknown or inactive service code(s): {', '.join(missing)}")
    allowed = _allowed_status_codes()
    for item in items:
        code = item["code"]
        stype = types[code]
        status_raw = (item.get("inspection_status") or "").strip()
        if status_raw and status_raw not in allowed:
            status_raw = ""
        remark_raw = item.get("remark") or ""
        StructureEntryServiceState.objects.update_or_create(
            structure_entry=entry,
            service_type=stype,
            defaults={
                "inspection_status": status_raw,
                "remark": remark_raw,
            },
        )


def build_services_representation(entry: StructureEntry) -> list[dict[str, str]]:
    """Sorted, self-describing list for JSON (read)."""
    rows = (
        StructureEntryServiceState.objects.filter(structure_entry=entry)
        .select_related("service_type")
        .order_by("service_type__sort_order", "service_type__code", "pk")
    )
    return [
        {
            "code": r.service_type.code,
            "label": r.service_type.label,
            "inspection_status": r.inspection_status or "",
            "remark": r.remark or "",
        }
        for r in rows
    ]


def delete_service_state_for_code(entry: StructureEntry, code: str) -> None:
    StructureEntryServiceState.objects.filter(
        structure_entry=entry, service_type__code=code
    ).delete()


@transaction.atomic
def ensure_default_service_types() -> None:
    """Idempotent bootstrap (migrations normally seed rows)."""
    for i, code in enumerate(LEGACY_CODES):
        InfraServiceType.objects.get_or_create(
            code=code,
            defaults={
                "label": _DEFAULT_LABELS[code],
                "sort_order": i,
                "active": True,
            },
        )
