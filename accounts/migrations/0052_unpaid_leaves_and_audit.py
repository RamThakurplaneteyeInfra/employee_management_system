"""
Add casual -> earn -> unpaid waterfall accounting.

Pure additive migration:
- LeaveSummary.unpaid_leaves: cumulative unpaid days for the user.
- LeaveApplicationData.casual_used / earn_used / unpaid_used: per-application split
  filled when MD approves a Full_day or Half_day leave.

No existing column or row is modified or deleted; defaults to 0 for every existing row.
"""
from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0051_menstrual_leave_reset"),
    ]

    operations = [
        migrations.AddField(
            model_name="leavesummary",
            name="unpaid_leaves",
            field=models.DecimalField(
                decimal_places=1,
                default=Decimal("0"),
                max_digits=6,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="leaveapplicationdata",
            name="casual_used",
            field=models.DecimalField(decimal_places=1, default=Decimal("0"), max_digits=5),
        ),
        migrations.AddField(
            model_name="leaveapplicationdata",
            name="earn_used",
            field=models.DecimalField(decimal_places=1, default=Decimal("0"), max_digits=5),
        ),
        migrations.AddField(
            model_name="leaveapplicationdata",
            name="unpaid_used",
            field=models.DecimalField(decimal_places=1, default=Decimal("0"), max_digits=5),
        ),
    ]
