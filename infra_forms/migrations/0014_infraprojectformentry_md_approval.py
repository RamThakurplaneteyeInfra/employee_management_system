# MD approval on InfraProjectFormEntry; backfill existing rows as Approved.

from django.db import migrations, models
from django.utils import timezone


def backfill_existing_entries_approved(apps, schema_editor):
    InfraProjectFormEntry = apps.get_model("infra_forms", "InfraProjectFormEntry")
    now = timezone.now()
    InfraProjectFormEntry.objects.all().update(
        approval="Approved",
        approved_at=now,
        approved_by="migration",
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("infra_forms", "0013_infra_service_types_and_states"),
    ]

    operations = [
        migrations.AddField(
            model_name="infraprojectformentry",
            name="approval",
            field=models.CharField(
                choices=[
                    ("Pending", "Pending"),
                    ("Approved", "Approved"),
                    ("Rejected", "Rejected"),
                ],
                db_index=True,
                default="Pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="infraprojectformentry",
            name="approval_note",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="infraprojectformentry",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="infraprojectformentry",
            name="approved_by",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.RunPython(backfill_existing_entries_approved, noop_reverse),
    ]
