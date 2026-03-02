# Reference from attachment to message (0012-style): MessageAttachment.group_message / individual_message
# Solves unattached links: attachment holds the FK to the message.

from django.db import migrations, models
import django.db.models.deletion


def migrate_message_attachment_to_attachment_ref(apps, schema_editor):
    """Copy message.attachment_id onto attachment: set attachment.group_message or individual_message."""
    GroupMessages = apps.get_model("Messaging", "GroupMessages")
    IndividualMessages = apps.get_model("Messaging", "IndividualMessages")
    MessageAttachment = apps.get_model("Messaging", "MessageAttachment")
    for msg in GroupMessages.objects.filter(attachment_id__isnull=False):
        MessageAttachment.objects.filter(pk=msg.attachment_id).update(
            group_message_id=msg.id,
            group_id=None,
            chat_id=None,
        )
    for msg in IndividualMessages.objects.filter(attachment_id__isnull=False):
        MessageAttachment.objects.filter(pk=msg.attachment_id).update(
            individual_message_id=msg.id,
            group_id=None,
            chat_id=None,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("Messaging", "0016_simple_attachment_fk_remove_link"),
    ]

    operations = [
        # 1. Add group_message and individual_message to MessageAttachment
        migrations.AddField(
            model_name="messageattachment",
            name="group_message",
            field=models.ForeignKey(
                blank=True,
                db_column="group_message_id",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attachments",
                to="Messaging.groupmessages",
            ),
        ),
        migrations.AddField(
            model_name="messageattachment",
            name="individual_message",
            field=models.ForeignKey(
                blank=True,
                db_column="individual_message_id",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attachments",
                to="Messaging.individualmessages",
            ),
        ),
        # 2. Backfill: set attachment.group_message/individual_message from message.attachment_id
        migrations.RunPython(migrate_message_attachment_to_attachment_ref, noop),
        # 3. Remove attachment FK from message models
        migrations.RemoveField(
            model_name="groupmessages",
            name="attachment",
        ),
        migrations.RemoveField(
            model_name="individualmessages",
            name="attachment",
        ),
    ]
