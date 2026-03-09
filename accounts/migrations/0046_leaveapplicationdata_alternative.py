# Add alternative (FK to User) to LeaveApplicationData - user who covers while applicant is on leave.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0045_leavesummary_emergency_leaves"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaveapplicationdata",
            name="alternative",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="leave_applications_as_alternative",
                to=settings.AUTH_USER_MODEL,
                db_column="alternative_id",
            ),
        ),
    ]
