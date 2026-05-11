# Monthly short-leave quota on LeaveSummary + idempotency flag on applications.
# Adds columns only; seeds existing summaries (no deletes).

from django.db import migrations, models
from django.utils import timezone


def seed_short_leave_month_stamp(apps, schema_editor):
    LeaveSummary = apps.get_model("accounts", "LeaveSummary")
    today = timezone.now().date()
    month_first = today.replace(day=1)
    LeaveSummary.objects.all().update(
        short_leaves_remaining=2,
        short_leave_credit_month_first=month_first,
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0056_short_leave_and_nullable_md"),
    ]

    operations = [
        migrations.AddField(
            model_name="leavesummary",
            name="short_leaves_remaining",
            field=models.PositiveSmallIntegerField(default=2),
        ),
        migrations.AddField(
            model_name="leavesummary",
            name="short_leave_credit_month_first",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaveapplicationdata",
            name="short_leave_slot_consumed",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(seed_short_leave_month_stamp, noop_reverse),
    ]
