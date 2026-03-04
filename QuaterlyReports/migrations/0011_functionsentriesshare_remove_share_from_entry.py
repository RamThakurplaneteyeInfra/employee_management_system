# Share chain: new FunctionsEntriesShare; migrate share_with/shared_Status into it; remove from FunctionsEntries.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_share_to_chain(apps, schema_editor):
    FunctionsEntries = apps.get_model("QuaterlyReports", "FunctionsEntries")
    FunctionsEntriesShare = apps.get_model("QuaterlyReports", "FunctionsEntriesShare")
    TaskStatus = apps.get_model("task_management", "TaskStatus")
    try:
        pending = TaskStatus.objects.filter(status_name="PENDING").first()
        pending_id = pending.id if pending else None
    except Exception:
        pending_id = None
    for entry in FunctionsEntries.objects.all():
        share_with_id = getattr(entry, "share_with_id", None)
        if not share_with_id:
            continue
        shared_status_id = getattr(entry, "shared_Status_id", None) or pending_id
        FunctionsEntriesShare.objects.get_or_create(
            actionable_entry=entry,
            shared_with_id=share_with_id,
            defaults={
                "note": getattr(entry, "note", "") or "",
                "individual_status_id": shared_status_id,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("task_management", "0024_alter_task_options"),
        ("QuaterlyReports", "0010_alter_functionsentries_final_status_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FunctionsEntriesShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("note", models.TextField(blank=True)),
                ("shared_time", models.DateTimeField(auto_now_add=True)),
                (
                    "actionable_entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="share_chain",
                        to="QuaterlyReports.functionsentries",
                        db_column="actionable_entry_id",
                    ),
                ),
                (
                    "shared_with",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to_field="username",
                        related_name="shared_entries_chain",
                        to=settings.AUTH_USER_MODEL,
                        db_column="shared_with",
                    ),
                ),
                (
                    "individual_status",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="functions_entries_share_status",
                        to="task_management.taskstatus",
                        db_column="individual_status_id",
                    ),
                ),
            ],
            options={
                "db_table": 'quatery_reports"."FunctionsEntriesShare',
                "ordering": ["shared_time"],
                "unique_together": {("actionable_entry", "shared_with")},
            },
        ),
        migrations.RunPython(migrate_share_to_chain, noop),
        migrations.RemoveField(
            model_name="functionsentries",
            name="shared_Status",
        ),
        migrations.RemoveField(
            model_name="functionsentries",
            name="share_with",
        ),
    ]
