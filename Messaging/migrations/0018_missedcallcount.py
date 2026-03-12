# MissedCallCount: one row per user, stores missed_call_count (updated by GET missedCallsCount/, reset by POST resetMissedCallsCount/)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("Messaging", "0017_attachment_refs_message"),
    ]

    operations = [
        migrations.CreateModel(
            name="MissedCallCount",
            fields=[
                (
                    "user",
                    models.OneToOneField(
                        db_column="user_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="messaging_missed_call_count",
                        serialize=False,
                        to=settings.AUTH_USER_MODEL,
                        to_field="username",
                    ),
                ),
                ("missed_call_count", models.IntegerField(db_column="missed_call_count", default=0)),
            ],
            options={
                "db_table": 'messaging"."MissedCallCount',
                "verbose_name": "Missed call count",
                "verbose_name_plural": "Missed call counts",
            },
        ),
    ]
