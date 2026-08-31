# Generated manually for FarmServiceTask.completed_at

from django.db import migrations, models
from django.db.models import F


def backfill_completed_at(apps, schema_editor):
    FarmServiceTask = apps.get_model("farm_services", "FarmServiceTask")
    FarmServiceTask.objects.filter(status=True, completed_at__isnull=True).update(
        completed_at=F("updated_at")
    )


def clear_completed_at(apps, schema_editor):
    FarmServiceTask = apps.get_model("farm_services", "FarmServiceTask")
    FarmServiceTask.objects.update(completed_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ("farm_services", "0004_farmservicerequest_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmservicetask",
            name="completed_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Set when status becomes true; used for performance scoring month.",
                null=True,
            ),
        ),
        migrations.RunPython(backfill_completed_at, clear_completed_at),
    ]
