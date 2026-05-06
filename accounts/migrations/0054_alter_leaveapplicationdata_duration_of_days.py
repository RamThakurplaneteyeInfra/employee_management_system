"""
Widen LeaveApplicationData.duration_of_days from SmallIntegerField to
DecimalField(max_digits=5, decimal_places=1) so half-day values (e.g. 0.5, 1.5)
can be stored.

PostgreSQL casts the existing smallint column to numeric(5,1) without data loss
(1 -> 1.0, 2 -> 2.0, ...). Only this single column is altered; every other
column on every other table is left exactly as it was.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0053_leavesummary_credit_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="leaveapplicationdata",
            name="duration_of_days",
            field=models.DecimalField(decimal_places=1, max_digits=5),
        ),
    ]
