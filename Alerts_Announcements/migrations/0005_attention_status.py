from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Alerts_Announcements", "0004_attention_target_employee"),
    ]

    operations = [
        migrations.AddField(
            model_name="attention",
            name="status",
            field=models.IntegerField(
                choices=[(1, "pending"), (2, "in_progress"), (3, "complete")],
                default=1,  # pending
            ),
        ),
    ]

