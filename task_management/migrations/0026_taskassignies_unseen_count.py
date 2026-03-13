# Generated manually for task-wise individual unseen count

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('task_management', '0025_remove_taskmessage_seen'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskassignies',
            name='unseen_count',
            field=models.PositiveSmallIntegerField(db_column='unseen_count', default=0),
        ),
    ]
