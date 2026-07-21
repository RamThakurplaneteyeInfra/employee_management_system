# Add created_by to CustomerPanelAmountLog and backfill existing rows
# with the parent entry's created_by so old logs are not orphaned.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_created_by(apps, schema_editor):
    CustomerPanelAmountLog = apps.get_model("CustomerPanel", "CustomerPanelAmountLog")
    CustomerPanelEntry = apps.get_model("CustomerPanel", "CustomerPanelEntry")

    entry_creator = {
        pk: creator_id
        for pk, creator_id in CustomerPanelEntry.objects.values_list("pk", "created_by_id")
    }
    to_update = []
    for log in CustomerPanelAmountLog.objects.filter(created_by__isnull=True).only("pk", "entry_id"):
        creator_id = entry_creator.get(log.entry_id)
        if creator_id is not None:
            log.created_by_id = creator_id
            to_update.append(log)
    if to_update:
        CustomerPanelAmountLog.objects.bulk_update(to_update, ["created_by"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("CustomerPanel", "0005_customerpanelentry_division"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="customerpanelamountlog",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="customer_panel_amount_logs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_created_by, migrations.RunPython.noop),
    ]
