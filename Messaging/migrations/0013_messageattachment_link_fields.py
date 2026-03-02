# Add link sharing: link_url, link_title; allow null s3_key/file_name for link-only attachments

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Messaging", "0012_messageattachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="messageattachment",
            name="link_url",
            field=models.URLField(blank=True, db_column="link_url", max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name="messageattachment",
            name="link_title",
            field=models.CharField(blank=True, db_column="link_title", max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name="messageattachment",
            name="s3_key",
            field=models.CharField(blank=True, db_column="s3_key", max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name="messageattachment",
            name="file_name",
            field=models.CharField(blank=True, db_column="file_name", max_length=255, null=True),
        ),
    ]
