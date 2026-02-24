# Generated manually: last_message_at DateField -> DateTimeField for date+time in IST in load_groups_and_chats

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Messaging', '0010_alter_groupchats_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupchats',
            name='last_message_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='individualchats',
            name='last_message_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
