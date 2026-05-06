"""
Add idempotency columns for the auto-credit jobs.

Pure additive migration:
- LeaveSummary.last_earn_credit_on   (DateField, nullable)
- LeaveSummary.last_casual_credit_on (DateField, nullable)

These columns let `credit_earn_leave` and `credit_casual_leave` skip rows that
have already been credited in the current month / quarter, so accidental
re-runs of the scheduled job are no-ops.

Existing rows are seeded with today's date so that the FIRST scheduled run
(which will fire on a future month/quarter boundary) does NOT re-credit the
already-loaded current period. Only the two new columns are touched - every
other column on every other table is left exactly as it was.
"""
from django.db import migrations, models
from django.utils import timezone


def seed_credit_dates(apps, schema_editor):
    """Stamp today on every existing LeaveSummary row.

    This is intentionally a bulk UPDATE that only writes the two new columns;
    no other field on LeaveSummary, no other model, no other row is touched.
    """
    LeaveSummary = apps.get_model("accounts", "LeaveSummary")
    today = timezone.localdate()
    LeaveSummary.objects.all().update(
        last_earn_credit_on=today,
        last_casual_credit_on=today,
    )


def unseed_credit_dates(apps, schema_editor):
    """Reverse step: clear the two columns. Schema removal happens separately."""
    LeaveSummary = apps.get_model("accounts", "LeaveSummary")
    LeaveSummary.objects.all().update(
        last_earn_credit_on=None,
        last_casual_credit_on=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0052_unpaid_leaves_and_audit"),
    ]

    operations = [
        migrations.AddField(
            model_name="leavesummary",
            name="last_earn_credit_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leavesummary",
            name="last_casual_credit_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(seed_credit_dates, reverse_code=unseed_credit_dates),
    ]
