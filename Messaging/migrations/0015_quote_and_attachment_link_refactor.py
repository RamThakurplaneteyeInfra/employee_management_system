# Quote (reply-with-quote) and MessageAttachmentLink refactor: group/chat + quote, remove message refs

from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion


def migrate_link_to_group_chat(apps, schema_editor):
    """Set group_id/chat_id on MessageAttachmentLink from the linked message, then clear message refs."""
    MessageAttachmentLink = apps.get_model("Messaging", "MessageAttachmentLink")
    GroupMessages = apps.get_model("Messaging", "GroupMessages")
    IndividualMessages = apps.get_model("Messaging", "IndividualMessages")
    for link in MessageAttachmentLink.objects.all():
        if link.group_message_id:
            try:
                msg = GroupMessages.objects.get(pk=link.group_message_id)
                link.group_id = msg.group_id
            except GroupMessages.DoesNotExist:
                pass
            link.group_message_id = None
        elif link.individual_message_id:
            try:
                msg = IndividualMessages.objects.get(pk=link.individual_message_id)
                link.chat_id = msg.chat_id
            except IndividualMessages.DoesNotExist:
                pass
            link.individual_message_id = None
        link.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("Messaging", "0014_m2m_message_attachment_link"),
    ]

    operations = [
        # 1. Add quoted_message to GroupMessages and IndividualMessages
        migrations.AddField(
            model_name="groupmessages",
            name="quoted_message",
            field=models.ForeignKey(
                blank=True,
                db_column="quoted_message_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replies",
                to="Messaging.groupmessages",
            ),
        ),
        migrations.AddField(
            model_name="individualmessages",
            name="quoted_message",
            field=models.ForeignKey(
                blank=True,
                db_column="quoted_message_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replies",
                to="Messaging.individualmessages",
            ),
        ),
        # 2. Add new fields to MessageAttachmentLink (group, chat, quote_*, created_at)
        migrations.AddField(
            model_name="messageattachmentlink",
            name="group",
            field=models.ForeignKey(
                blank=True,
                db_column="group_id",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attachment_links",
                to="Messaging.groupchats",
            ),
        ),
        migrations.AddField(
            model_name="messageattachmentlink",
            name="chat",
            field=models.ForeignKey(
                blank=True,
                db_column="chat_id",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attachment_links",
                to="Messaging.individualchats",
            ),
        ),
        migrations.AddField(
            model_name="messageattachmentlink",
            name="quote_group_message",
            field=models.ForeignKey(
                blank=True,
                db_column="quote_group_message_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="Messaging.groupmessages",
            ),
        ),
        migrations.AddField(
            model_name="messageattachmentlink",
            name="quote_individual_message",
            field=models.ForeignKey(
                blank=True,
                db_column="quote_individual_message_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="Messaging.individualmessages",
            ),
        ),
        migrations.AddField(
            model_name="messageattachmentlink",
            name="created_at",
            field=models.DateTimeField(db_column="created_at", default=timezone.now),
        ),
        # 3. Backfill group_id/chat_id from group_message/individual_message
        migrations.RunPython(migrate_link_to_group_chat, noop),
        # 4. Remove old FKs from MessageAttachmentLink
        migrations.RemoveField(
            model_name="messageattachmentlink",
            name="group_message",
        ),
        migrations.RemoveField(
            model_name="messageattachmentlink",
            name="individual_message",
        ),
        # 5. Switch created_at to auto_now_add
        migrations.AlterField(
            model_name="messageattachmentlink",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_column="created_at"),
        ),
    ]
