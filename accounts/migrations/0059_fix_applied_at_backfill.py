"""
Correct applied_at for rows stamped at migration time (0058 AddField default).

- Rows where IST date of applied_at != application_date → midnight IST on application_date.
- Rows sharing the most common applied_at (bulk migration stamp) → same midnight rule.
- New submissions with a real time on the correct day are kept when they are not the bulk stamp.
"""

from datetime import datetime, time

from django.db import migrations
from django.db.models import Count
from django.utils import timezone


def _midnight_ist(application_date, ist):
    return timezone.make_aware(datetime.combine(application_date, time.min), ist)


def fix_applied_at_backfill(apps, schema_editor):
    LeaveApplicationData = apps.get_model("accounts", "LeaveApplicationData")
    ist = timezone.get_fixed_timezone(330)

    bulk_stamp = (
        LeaveApplicationData.objects.filter(applied_at__isnull=False)
        .values("applied_at")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
        .order_by("-row_count")
        .first()
    )
    stamp_value = bulk_stamp["applied_at"] if bulk_stamp else None

    for row in LeaveApplicationData.objects.all().iterator():
        if not row.application_date:
            continue

        target = _midnight_ist(row.application_date, ist)
        needs_fix = False

        if not row.applied_at:
            needs_fix = True
        else:
            applied_ist = row.applied_at.astimezone(ist)
            if applied_ist.date() != row.application_date:
                needs_fix = True
            elif stamp_value is not None and row.applied_at == stamp_value:
                needs_fix = True

        if needs_fix:
            LeaveApplicationData.objects.filter(pk=row.pk).update(applied_at=target)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0058_leaveapplicationdata_applied_at"),
    ]

    operations = [
        migrations.RunPython(fix_applied_at_backfill, migrations.RunPython.noop),
    ]
