# Simple messaging: message.attachment FK, remove quoted_message and MessageAttachmentLink

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("Messaging", "0015_quote_and_attachment_link_refactor"),
    ]

    operations = [
        # 1. Add attachment FK to GroupMessages and IndividualMessages
        migrations.AddField(
            model_name="groupmessages",
            name="attachment",
            field=models.ForeignKey(
                blank=True,
                db_column="attachment_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="group_messages",
                to="Messaging.messageattachment",
            ),
        ),
        migrations.AddField(
            model_name="individualmessages",
            name="attachment",
            field=models.ForeignKey(
                blank=True,
                db_column="attachment_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="individual_messages",
                to="Messaging.messageattachment",
            ),
        ),
        # 2. Remove quoted_message from both
        migrations.RemoveField(
            model_name="groupmessages",
            name="quoted_message",
        ),
        migrations.RemoveField(
            model_name="individualmessages",
            name="quoted_message",
        ),
        # 3. Remove MessageAttachmentLink model (drops table)
        migrations.DeleteModel(
            name="MessageAttachmentLink",
        ),
    ]
