# Generated manually for alternative accept/reject workflow

from django.db import migrations, models
import django.db.models.deletion


def backfill_alternative_pending(apps, schema_editor):
    """Existing rows with an alternative but no MD approval: set alternative_approval to Pending."""
    LeaveApplicationData = apps.get_model("accounts", "LeaveApplicationData")
    LeaveStatus = apps.get_model("accounts", "LeaveStatus")
    pending = LeaveStatus.objects.filter(name="Pending").first()
    if not pending:
        return
    LeaveApplicationData.objects.filter(
        alternative_id__isnull=False,
        alternative_approval_id__isnull=True,
    ).exclude(MD_approval__name="Approved").update(alternative_approval_id=pending.pk)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0054_alter_leaveapplicationdata_duration_of_days"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaveapplicationdata",
            name="alternative_approval",
            field=models.ForeignKey(
                blank=True,
                db_column="alternative_approval_id",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="accounts.leavestatus",
            ),
        ),
        migrations.AddField(
            model_name="leaveapplicationdata",
            name="alternative_responded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_alternative_pending, noop_reverse),
    ]
