# Short leave: optional start time; MD_approval nullable for TL→HR→Admin flow;
# seed Short Leave type (additive only).

import accounts.models
from django.db import migrations, models
import django.db.models.deletion


def ensure_short_leave_type(apps, schema_editor):
    LeaveTypes = apps.get_model("accounts", "LeaveTypes")
    LeaveTypes.objects.get_or_create(name="Short Leave")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0055_leaveapplicationdata_alternative_approval"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaveapplicationdata",
            name="short_leave_start_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="leaveapplicationdata",
            name="MD_approval",
            field=models.ForeignKey(
                blank=True,
                db_column="md_approval_id",
                default=accounts.models._get_pending_leave_status_id,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="accounts.leavestatus",
            ),
        ),
        migrations.RunPython(ensure_short_leave_type, noop_reverse),
    ]
