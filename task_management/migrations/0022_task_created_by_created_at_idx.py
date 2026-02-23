# Generated manually for query optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('task_management', '0021_alter_task_task_id'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='task',
            index=models.Index(fields=['created_by', '-created_at'], name='task_created_by_created_at_idx'),
        ),
        migrations.AddIndex(
            model_name='task',
            index=models.Index(fields=['created_by', 'type'], name='task_created_by_type_idx'),
        ),
    ]
