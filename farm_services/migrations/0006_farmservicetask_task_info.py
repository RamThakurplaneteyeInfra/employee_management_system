from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("farm_services", "0005_farmservicetask_completed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmservicetask",
            name="task_info",
            field=models.TextField(blank=True, default=""),
        ),
    ]
