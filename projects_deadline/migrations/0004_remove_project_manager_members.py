"""
Remove manager ForeignKey and members ManyToManyField from DeadlineProject.
Only affects the new (empty) DeadlineProject table — no existing data is touched.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("projects_deadline", "0003_uuid_to_int_pk"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="deadlineproject",
            name="manager",
        ),
        migrations.RemoveField(
            model_name="deadlineproject",
            name="members",
        ),
    ]
