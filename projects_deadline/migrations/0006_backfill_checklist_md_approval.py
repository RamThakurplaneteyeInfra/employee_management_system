# Backfill checklist MD approval fields on existing phase checklist JSON.
# Checked items → Approved (preserve historical scoring); unchecked → Pending.

import uuid

from django.db import migrations

MD_APPROVED = "Approved"
MD_PENDING = "Pending"


def _backfill_checklist(checklist):
    if not isinstance(checklist, list):
        return checklist, False
    changed = False
    out = []
    for item in checklist:
        if not isinstance(item, dict):
            out.append(item)
            continue
        row = dict(item)
        if not row.get("id"):
            row["id"] = str(uuid.uuid4())
            changed = True
        checked = bool(row.get("checked"))
        status = (row.get("mdApproval") or "").strip() if isinstance(row.get("mdApproval"), str) else ""
        if not status:
            row["mdApproval"] = MD_APPROVED if checked else MD_PENDING
            changed = True
        if "mdApprovedAt" not in row:
            row["mdApprovedAt"] = None
            changed = True
        if "mdApprovedBy" not in row:
            row["mdApprovedBy"] = None
            changed = True
        if "mdNote" not in row:
            row["mdNote"] = ""
            changed = True
        out.append(row)
    return out, changed


def backfill_md_approval(apps, schema_editor):
    DeadlineProjectPhase = apps.get_model("projects_deadline", "DeadlineProjectPhase")
    batch = []
    for phase in DeadlineProjectPhase.objects.all().only("id", "checklist").iterator(chunk_size=200):
        new_checklist, changed = _backfill_checklist(phase.checklist)
        if changed:
            phase.checklist = new_checklist
            batch.append(phase)
        if len(batch) >= 100:
            DeadlineProjectPhase.objects.bulk_update(batch, ["checklist"], batch_size=100)
            batch = []
    if batch:
        DeadlineProjectPhase.objects.bulk_update(batch, ["checklist"], batch_size=100)


class Migration(migrations.Migration):

    dependencies = [
        ("projects_deadline", "0005_phase_plain_ids"),
    ]

    operations = [
        migrations.RunPython(backfill_md_approval, migrations.RunPython.noop),
    ]
