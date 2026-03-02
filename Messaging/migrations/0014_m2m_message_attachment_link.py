# M2M: MessageAttachmentLink; MessageAttachment gets group/chat for attachment-only; remove direct message FKs

from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


def migrate_attachments_to_links(apps, schema_editor):
    MessageAttachment = apps.get_model("Messaging", "MessageAttachment")
    MessageAttachmentLink = apps.get_model("Messaging", "MessageAttachmentLink")
    qs = MessageAttachment.objects.filter(
        Q(group_message_id__isnull=False) | Q(individual_message_id__isnull=False)
    )
    # Use list() to avoid server-side cursor (PostgreSQL "cursor FOR SET" syntax error in migrations)
    for att in list(qs):
        MessageAttachmentLink.objects.get_or_create(
            attachment_id=att.id,
            defaults={
                "group_message_id": getattr(att, "group_message_id", None),
                "individual_message_id": getattr(att, "individual_message_id", None),
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("Messaging", "0013_messageattachment_link_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="messageattachment",
            name="group",
            field=models.ForeignKey(
                blank=True,
                db_column="group_id",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="standalone_attachments",
                to="Messaging.groupchats",
            ),
        ),
        migrations.AddField(
            model_name="messageattachment",
            name="chat",
            field=models.ForeignKey(
                blank=True,
                db_column="chat_id",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="standalone_attachments",
                to="Messaging.individualchats",
            ),
        ),
        migrations.CreateModel(
            name="MessageAttachmentLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "attachment",
                    models.ForeignKey(
                        db_column="attachment_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="message_links",
                        to="Messaging.messageattachment",
                    ),
                ),
                (
                    "group_message",
                    models.ForeignKey(
                        blank=True,
                        db_column="group_message_id",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachment_links",
                        to="Messaging.groupmessages",
                    ),
                ),
                (
                    "individual_message",
                    models.ForeignKey(
                        blank=True,
                        db_column="individual_message_id",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachment_links",
                        to="Messaging.individualmessages",
                    ),
                ),
            ],
            options={
                "verbose_name": "Message–attachment link",
                "db_table": 'messaging"."MessageAttachmentLinks',
            },
        ),
        migrations.RunPython(migrate_attachments_to_links, noop),
        migrations.RemoveField(
            model_name="messageattachment",
            name="group_message",
        ),
        migrations.RemoveField(
            model_name="messageattachment",
            name="individual_message",
        ),
    ]
