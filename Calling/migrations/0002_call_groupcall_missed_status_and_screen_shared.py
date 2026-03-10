# Add MISSED status choice and is_screen_shared to Call and GroupCall.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Calling", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="call",
            name="is_screen_shared",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="call",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                    ("ended", "Ended"),
                    ("missed", "Missed"),
                ],
                default="pending",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="groupcall",
            name="is_screen_shared",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="groupcall",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("ended", "Ended"),
                    ("missed", "Missed"),
                ],
                default="active",
                max_length=10,
            ),
        ),
    ]
