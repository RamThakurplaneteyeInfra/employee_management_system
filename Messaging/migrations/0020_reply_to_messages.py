# WhatsApp-style reply-to (non-destructive AddField only)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("Messaging", "0019_delete_missedcallcount"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # DB already contains reply_to_id columns in your environment.
            # Keep database operations empty to avoid "duplicate column" failures.
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="groupmessages",
                    name="reply_to",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="reply_to_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="group_replies",
                        to="Messaging.groupmessages",
                    ),
                ),
                migrations.AddField(
                    model_name="individualmessages",
                    name="reply_to",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="reply_to_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dm_replies",
                        to="Messaging.individualmessages",
                    ),
                ),
            ],
        ),
    ]

