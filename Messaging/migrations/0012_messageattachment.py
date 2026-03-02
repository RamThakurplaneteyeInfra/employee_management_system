# Generated for MessageAttachment (S3 file paths in messaging schema)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("Messaging", "0011_alter_groupchats_last_message_at_alter_individualchats_last_message_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("s3_key", models.CharField(db_column="s3_key", max_length=512)),
                ("file_name", models.CharField(db_column="file_name", max_length=255)),
                ("content_type", models.CharField(blank=True, db_column="content_type", max_length=128, null=True)),
                ("file_size", models.PositiveIntegerField(blank=True, db_column="file_size", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="created_at")),
                (
                    "group_message",
                    models.ForeignKey(
                        blank=True,
                        db_column="group_message_id",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
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
                        related_name="attachments",
                        to="Messaging.individualmessages",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        db_column="uploaded_by",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messaging_attachments",
                        to=settings.AUTH_USER_MODEL,
                        to_field="username",
                    ),
                ),
            ],
            options={
                "verbose_name": "Message attachment",
                "db_table": 'messaging"."MessageAttachments',
                "ordering": ["created_at"],
            },
        ),
    ]
