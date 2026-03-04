# LeaveStatus (Approved, Pending, Rejected) and LeaveApplicationData in team_management schema

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def insert_leave_statuses(apps, schema_editor):
    LeaveStatus = apps.get_model("accounts", "LeaveStatus")
    for name in ("Approved", "Pending", "Rejected"):
        LeaveStatus.objects.get_or_create(name=name)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0040_leavesummary_leavetypes"),
    ]

    operations = [
        migrations.CreateModel(
            name="LeaveStatus",
            fields=[
                ("id", models.AutoField(primary_key=True, auto_created=True, serialize=False)),
                ("name", models.CharField(max_length=20, unique=True)),
            ],
            options={
                "db_table": 'team_management"."leave_status',
                "verbose_name": "leave status",
                "verbose_name_plural": "leave statuses",
            },
        ),
        migrations.RunPython(insert_leave_statuses, noop),
        migrations.CreateModel(
            name="LeaveApplicationData",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("duration_of_days", models.SmallIntegerField()),
                ("live_subject", models.CharField(max_length=255)),
                ("reason", models.TextField()),
                ("half_day_slots", models.CharField(blank=True, choices=[("First Half", "First Half"), ("Second half", "Second half")], max_length=20, null=True)),
                ("is_emergency", models.BooleanField(default=False)),
                ("application_date", models.DateField(auto_now_add=True)),
                ("approved_by_MD_at", models.DateTimeField(blank=True, null=True)),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="leave_applications",
                        to=settings.AUTH_USER_MODEL,
                        db_column="applicant_id",
                    ),
                ),
                (
                    "leave_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="leave_applications",
                        to="accounts.leavetypes",
                        db_column="leave_type_id",
                    ),
                ),
                (
                    "team_lead_approval",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="accounts.leavestatus",
                        db_column="team_lead_approval_id",
                    ),
                ),
                (
                    "HR_approval",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="accounts.leavestatus",
                        db_column="hr_approval_id",
                    ),
                ),
                (
                    "MD_approval",
                    models.ForeignKey(
                        default=2,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="accounts.leavestatus",
                        db_column="md_approval_id",
                    ),
                ),
                (
                    "admin_approval",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="accounts.leavestatus",
                        db_column="admin_approval_id",
                    ),
                ),
            ],
            options={
                "db_table": 'team_management"."leave_application_data',
                "verbose_name": "leave application",
                "verbose_name_plural": "leave applications",
            },
        ),
    ]
