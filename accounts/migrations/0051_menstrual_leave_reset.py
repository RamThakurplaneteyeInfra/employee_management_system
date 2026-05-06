"""
Reset menstrual-leave semantics:
- Clamp existing values in `LeaveSummary.menstrual_leaves` to {0, 1}.
- Insert the `Menstrual` row in `LeaveTypes` if missing.
- Set `menstrual_leaves = 1` for all female employees, `0` for everyone else.
- Tighten the column to PositiveSmallIntegerField with MaxValueValidator(1).
"""
import django.core.validators
from django.db import migrations, models


def _seed_menstrual_balances(apps, schema_editor):
    LeaveSummary = apps.get_model("accounts", "LeaveSummary")
    LeaveTypes = apps.get_model("accounts", "LeaveTypes")
    Profile = apps.get_model("accounts", "Profile")

    LeaveTypes.objects.get_or_create(name="Menstrual")

    female_usernames = list(
        Profile.objects.filter(gender__iexact="Female")
        .values_list("Employee_id__username", flat=True)
    )

    # Clamp any out-of-range historical values first so the AlterField is safe.
    # PositiveSmallInteger cannot hold negatives or values > 1 (after validator).
    # We do this column-wise: females -> 1, everyone else -> 0.
    LeaveSummary.objects.filter(user__username__in=female_usernames).update(
        menstrual_leaves=1
    )
    LeaveSummary.objects.exclude(user__username__in=female_usernames).update(
        menstrual_leaves=0
    )


def _noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0050_alter_leavesummary_casual_leaves_and_more"),
    ]

    operations = [
        migrations.RunPython(_seed_menstrual_balances, _noop_reverse),
        migrations.AlterField(
            model_name="leavesummary",
            name="menstrual_leaves",
            field=models.PositiveSmallIntegerField(
                default=0,
                validators=[django.core.validators.MaxValueValidator(1)],
            ),
        ),
    ]
