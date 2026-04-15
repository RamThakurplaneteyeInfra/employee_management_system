from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0003_alter_jobapplication_full_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobopening",
            name="job_state",
            field=models.CharField(
                choices=[("Open", "Open"), ("Closed", "Closed")],
                default="Open",
                help_text="Operational state controlled by Team Leads: Open/Closed.",
                max_length=10,
            ),
        ),
    ]
