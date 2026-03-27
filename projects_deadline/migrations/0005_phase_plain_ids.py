"""
Replace team_lead ForeignKey and members ManyToManyField on DeadlineProjectPhase
with plain IntegerField and JSONField — no FK constraints to auth_user.

Only affects the new (empty) DeadlineProjectPhase table. No existing data touched.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects_deadline", "0004_remove_project_manager_members"),
    ]

    operations = [
        # Drop the M2M join table (empty)
        migrations.RemoveField(
            model_name="deadlineprojectphase",
            name="members",
        ),
        # Drop the FK column (empty table)
        migrations.RemoveField(
            model_name="deadlineprojectphase",
            name="team_lead",
        ),
        # Add plain IntegerField for team_lead_id
        migrations.AddField(
            model_name="deadlineprojectphase",
            name="team_lead_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        # Add JSONField for member_ids
        migrations.AddField(
            model_name="deadlineprojectphase",
            name="member_ids",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
