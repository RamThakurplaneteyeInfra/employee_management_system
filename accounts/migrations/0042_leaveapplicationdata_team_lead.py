# Add team_lead to LeaveApplicationData (from Profile.Teamlead); backfill existing rows.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_team_lead(apps, schema_editor):
    LeaveApplicationData = apps.get_model("accounts", "LeaveApplicationData")
    Profile = apps.get_model("accounts", "Profile")
    User = apps.get_model(settings.AUTH_USER_MODEL)
    for app in list(LeaveApplicationData.objects.all()):
        try:
            user = User.objects.get(pk=app.applicant_id)
            profile = Profile.objects.get(Employee_id=user.username)
            app.team_lead_id = profile.Teamlead_id if profile.Teamlead_id else None
        except (Profile.DoesNotExist, User.DoesNotExist):
            app.team_lead_id = None
        app.save(update_fields=["team_lead_id"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0041_leave_status_and_leave_application_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaveapplicationdata",
            name="team_lead",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="leave_applications_as_teamlead",
                to=settings.AUTH_USER_MODEL,
                db_column="team_lead_id",
            ),
        ),
        migrations.RunPython(backfill_team_lead, noop),
    ]
